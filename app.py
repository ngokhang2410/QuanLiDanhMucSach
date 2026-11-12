from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Text, ForeignKey, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-chi-dung-khi-phat-trien"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quanlysach.db"

db.init_app(app)


class Category(db.Model):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    books: Mapped[list["Book"]] = relationship(back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"


class Book(db.Model):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(100))
    year: Mapped[int] = mapped_column(default=2020)
    available: Mapped[bool] = mapped_column(default=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))

    category: Mapped["Category"] = relationship(back_populates="books")

    def __repr__(self):
        return f"<Book {self.title}>"


with app.app_context():
    db.create_all()


def _seed_if_empty() -> bool:
    """Thêm dữ liệu mẫu nếu chưa có danh mục. Trả về True nếu đã seed."""
    total = db.session.scalar(select(func.count(Category.id)))
    if total and total > 0:
        return False

    lap_trinh = Category(name="Lập trình", description="Sách học ngôn ngữ và framework")
    khoa_hoc = Category(name="Khoa học máy tính", description="Cấu trúc dữ liệu, CSDL, thuật toán")
    kinh_te = Category(name="Kinh tế", description="Marketing, quản trị, kinh doanh")

    db.session.add_all([lap_trinh, khoa_hoc, kinh_te])
    db.session.flush()

    db.session.add_all(
        [
            Book(
                title="Lập trình Python Căn Bản",
                author="Nguyễn Văn A",
                year=2022,
                available=True,
                category_id=lap_trinh.id,
            ),
            Book(
                title="Flask Web Development",
                author="Miguel Grinberg",
                year=2018,
                available=False,
                category_id=lap_trinh.id,
            ),
            Book(
                title="Cấu Trúc Dữ Liệu và Giải Thuật",
                author="Trần Văn B",
                year=2020,
                available=True,
                category_id=khoa_hoc.id,
            ),
            Book(
                title="Thiết Kế Cơ Sở Dữ Liệu",
                author="Lê Văn C",
                year=2021,
                available=False,
                category_id=khoa_hoc.id,
            ),
            Book(
                title="Thấu Hiểu Tiếp Thị",
                author="Philip Kotler",
                year=2019,
                available=True,
                category_id=kinh_te.id,
            ),
        ]
    )
    db.session.commit()
    return True


# ---------- Dashboard ----------


@app.get("/")
def dashboard():
    total_categories = db.session.scalar(select(func.count(Category.id))) or 0
    total_books = db.session.scalar(select(func.count(Book.id))) or 0
    available_books = (
        db.session.scalar(select(func.count(Book.id)).where(Book.available.is_(True))) or 0
    )
    unavailable_books = total_books - available_books

    categories = db.session.execute(
        select(Category).order_by(Category.name)
    ).scalars().all()

    category_stats = [
        {
            "category": cat,
            "book_count": db.session.scalar(
                select(func.count(Book.id)).where(Book.category_id == cat.id)
            )
            or 0,
        }
        for cat in categories
    ]

    return render_template(
        "dashboard.html",
        total_categories=total_categories,
        total_books=total_books,
        available_books=available_books,
        unavailable_books=unavailable_books,
        category_stats=category_stats,
    )


# ---------- Seed ----------


@app.get("/seed")
def seed():
    if _seed_if_empty():
        flash("Đã thêm dữ liệu mẫu (3 danh mục, 5 sách).", "success")
    else:
        flash("Database đã có dữ liệu, không thêm mẫu nữa.", "warning")
    return redirect(url_for("dashboard"))


# ---------- CRUD Danh mục ----------


@app.get("/categories")
def categories_list():
    categories = db.session.execute(
        select(Category).order_by(Category.name)
    ).scalars().all()
    return render_template("categories/list.html", categories=categories)


@app.route("/categories/create", methods=["GET", "POST"])
def categories_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip() or None

        if not name:
            flash("Tên danh mục không được để trống.", "danger")
            return render_template("categories/form.html", category=None)

        exists = db.session.scalar(select(Category).filter_by(name=name))
        if exists:
            flash(f"Danh mục «{name}» đã tồn tại.", "danger")
            return render_template("categories/form.html", category=None)

        db.session.add(Category(name=name, description=description))
        db.session.commit()
        flash("Đã thêm danh mục.", "success")
        return redirect(url_for("categories_list"))

    return render_template("categories/form.html", category=None)


@app.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
def categories_edit(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip() or None

        if not name:
            flash("Tên danh mục không được để trống.", "danger")
            return render_template("categories/form.html", category=category)

        other = db.session.scalar(
            select(Category).where(Category.name == name, Category.id != category.id)
        )
        if other:
            flash(f"Danh mục «{name}» đã tồn tại.", "danger")
            return render_template("categories/form.html", category=category)

        category.name = name
        category.description = description
        db.session.commit()
        flash("Đã cập nhật danh mục.", "success")
        return redirect(url_for("categories_list"))

    return render_template("categories/form.html", category=category)


@app.post("/categories/<int:category_id>/delete")
def categories_delete(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        abort(404)

    book_count = db.session.scalar(
        select(func.count(Book.id)).where(Book.category_id == category.id)
    ) or 0
    if book_count > 0:
        flash(
            f"Không thể xóa «{category.name}» vì còn {book_count} sách. "
            "Hãy chuyển hoặc xóa sách trước.",
            "danger",
        )
        return redirect(url_for("categories_list"))

    db.session.delete(category)
    db.session.commit()
    flash("Đã xóa danh mục.", "success")
    return redirect(url_for("categories_list"))


# ---------- CRUD Sách ----------


@app.get("/books")
def books_list():
    category_id = request.args.get("category_id", type=int)
    categories = db.session.execute(
        select(Category).order_by(Category.name)
    ).scalars().all()

    stmt = select(Book).order_by(Book.id)
    if category_id:
        stmt = stmt.where(Book.category_id == category_id)

    books = db.session.execute(stmt).scalars().all()
    return render_template(
        "books/list.html",
        books=books,
        categories=categories,
        selected_category_id=category_id,
    )


@app.route("/books/create", methods=["GET", "POST"])
def books_create():
    categories = db.session.execute(
        select(Category).order_by(Category.name)
    ).scalars().all()

    if not categories:
        flash("Cần tạo ít nhất một danh mục trước khi thêm sách.", "warning")
        return redirect(url_for("categories_create"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        year_raw = request.form.get("year", "").strip()
        category_id = request.form.get("category_id", type=int)
        available = request.form.get("available") == "on"

        if not title or not author or not category_id:
            flash("Vui lòng nhập tiêu đề, tác giả và chọn danh mục.", "danger")
            return render_template("books/form.html", book=None, categories=categories)

        category = db.session.get(Category, category_id)
        if not category:
            flash("Danh mục không hợp lệ.", "danger")
            return render_template("books/form.html", book=None, categories=categories)

        try:
            year = int(year_raw) if year_raw else 2020
        except ValueError:
            flash("Năm xuất bản phải là số.", "danger")
            return render_template("books/form.html", book=None, categories=categories)

        db.session.add(
            Book(
                title=title,
                author=author,
                year=year,
                available=available,
                category_id=category_id,
            )
        )
        db.session.commit()
        flash("Đã thêm sách.", "success")
        return redirect(url_for("books_list"))

    return render_template("books/form.html", book=None, categories=categories)


@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
def books_edit(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)

    categories = db.session.execute(
        select(Category).order_by(Category.name)
    ).scalars().all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        year_raw = request.form.get("year", "").strip()
        category_id = request.form.get("category_id", type=int)
        available = request.form.get("available") == "on"

        if not title or not author or not category_id:
            flash("Vui lòng nhập tiêu đề, tác giả và chọn danh mục.", "danger")
            return render_template("books/form.html", book=book, categories=categories)

        category = db.session.get(Category, category_id)
        if not category:
            flash("Danh mục không hợp lệ.", "danger")
            return render_template("books/form.html", book=book, categories=categories)

        try:
            year = int(year_raw) if year_raw else book.year
        except ValueError:
            flash("Năm xuất bản phải là số.", "danger")
            return render_template("books/form.html", book=book, categories=categories)

        book.title = title
        book.author = author
        book.year = year
        book.available = available
        book.category_id = category_id
        db.session.commit()
        flash("Đã cập nhật sách.", "success")
        return redirect(url_for("books_list"))

    return render_template("books/form.html", book=book, categories=categories)


@app.post("/books/<int:book_id>/delete")
def books_delete(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        abort(404)

    db.session.delete(book)
    db.session.commit()
    flash("Đã xóa sách.", "success")
    return redirect(url_for("books_list"))


if __name__ == "__main__":
    app.run(debug=True)
