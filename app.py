from decimal import Decimal, InvalidOperation

from flask import Flask, render_template, request, redirect, url_for, flash, abort
from config import Config
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    current_user,
    logout_user,
)
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from models import db, Order, User
from security import encrypt_data, decrypt_data

app = Flask(__name__)
app.config.from_object(Config)

csrf = CSRFProtect(app)
bcrypt = Bcrypt(app)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Фиксированные тарифы (рубли). Клиент не может изменить их через форму.
DRILLING_PRICE_PER_METER = 2500
PIPE_PRICE_PER_METER = 900
ADDITIONAL_WORKS_PRICE = 50000


def calculate_estimate(depth):
    return (
        depth * Decimal(DRILLING_PRICE_PER_METER)
        + depth * Decimal(PIPE_PRICE_PER_METER)
        + Decimal(ADDITIONAL_WORKS_PRICE)
    ).quantize(Decimal("0.01"))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
def home():
    return render_template("main.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not all([login_value, full_name, phone, password]):
            return render_template("main.html", error="Заполните все поля")

        if len(password) < 8:
            return render_template(
                "main.html",
                error="Пароль должен содержать минимум 8 символов"
            )

        try:
            existing_user = User.query.filter_by(login=login_value).first()
            if existing_user:
                return render_template(
                    "main.html",
                    error="Этот логин уже занят"
                )

            new_user = User(
                login=login_value,
                full_name_encrypted=encrypt_data(full_name),
                phone_encrypted=encrypt_data(phone),
                password_hash=bcrypt.generate_password_hash(
                    password
                ).decode("utf-8"),
                role="client"
            )
            db.session.add(new_user)
            db.session.commit()

        except Exception:
            db.session.rollback()
            app.logger.exception("Ошибка при регистрации пользователя")
            return render_template(
                "main.html",
                error="Не удалось выполнить регистрацию. Проверьте консоль Flask."
            ), 500

        flash("Регистрация прошла успешно. Теперь войдите в аккаунт.")
        return redirect(url_for("login"))

    return render_template("main.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(login=login_value).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)

            if user.role == "employee":
                return redirect(url_for("employee_map"))
            if user.role == "client":
                return redirect(url_for("client_dashboard"))

            logout_user()
            return "Неизвестная роль пользователя", 403

        return render_template(
            "login.html",
            error="Неверный логин или пароль"
        ), 401

    return render_template("login.html")


@app.route("/client", methods=["GET", "POST"])
@login_required
def client_dashboard():
    if current_user.role != "client":
        abort(403)

    result = None
    depth_value = ""
    orders = Order.query.filter_by(client_id=current_user.id).order_by(Order.id.desc()).all()

    if request.method == "POST":
        depth_value = request.form.get("depth", "").strip()

        try:
            depth = Decimal(depth_value.replace(",", "."))

            if not depth.is_finite() or not 0 < depth <= 1000:
                raise ValueError("Недопустимая глубина")

            depth = depth.quantize(Decimal("0.01"))
            if depth <= 0:
                raise ValueError("Недопустимая глубина")

            drilling_cost = depth * Decimal(DRILLING_PRICE_PER_METER)
            pipe_cost = depth * Decimal(PIPE_PRICE_PER_METER)
            total = calculate_estimate(depth)

            result = {
                "depth": depth,
                "drilling_cost": drilling_cost,
                "pipe_cost": pipe_cost,
                "additional_works": ADDITIONAL_WORKS_PRICE,
                "total": total,
            }
        except (ValueError, TypeError, InvalidOperation):
            flash("Укажите корректную глубину: больше 0 и не более 1000 метров.")

    try:
        full_name = decrypt_data(current_user.full_name_encrypted)
    except Exception:
        app.logger.exception("Не удалось расшифровать ФИО пользователя")
        full_name = "Не удалось загрузить имя"

    return render_template(
        "client.html",
        full_name=full_name,
        depth=depth_value,
        result=result,
        orders=orders,
        drilling_price=DRILLING_PRICE_PER_METER,
        pipe_price=PIPE_PRICE_PER_METER,
        additional_price=ADDITIONAL_WORKS_PRICE,
    )


@app.route("/orders/create", methods=["POST"])
@login_required
def create_order():
    if current_user.role != "client":
        abort(403)

    try:
        depth = Decimal(request.form.get("depth", "").strip().replace(",", "."))
        latitude = Decimal(request.form.get("latitude", "").strip().replace(",", "."))
        longitude = Decimal(request.form.get("longitude", "").strip().replace(",", "."))

        if not depth.is_finite() or not 0 < depth <= 1000:
            raise ValueError("Недопустимая глубина")
        if not latitude.is_finite() or not Decimal("-90") <= latitude <= Decimal("90"):
            raise ValueError("Недопустимая широта")
        if not longitude.is_finite() or not Decimal("-180") <= longitude <= Decimal("180"):
            raise ValueError("Недопустимая долгота")

        depth = depth.quantize(Decimal("0.01"))
        if depth <= 0:
            raise ValueError("Недопустимая глубина")
        order = Order(
            client_id=current_user.id,
            depth=depth,
            latitude=latitude.quantize(Decimal("0.000001")),
            longitude=longitude.quantize(Decimal("0.000001")),
            price=calculate_estimate(depth),
        )
        db.session.add(order)
        db.session.commit()
        flash("Заявка успешно создана.")
    except (ValueError, TypeError, InvalidOperation):
        db.session.rollback()
        flash("Проверьте глубину и координаты. Широта: от -90 до 90, долгота: от -180 до 180.")
    except Exception:
        db.session.rollback()
        app.logger.exception("Не удалось сохранить заявку")
        flash("Не удалось сохранить заявку. Попробуйте ещё раз или обратитесь к сотруднику.")

    return redirect(url_for("client_dashboard"))


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, use_reloader=False)
