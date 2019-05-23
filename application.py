"""
This module describes whole server-side logic for the web application.
"""

import os
import requests

from flask import Flask, jsonify, render_template, request, redirect, session
from flask_bcrypt import Bcrypt
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    """
    Checks whether the user is stored in the session. If he is not redirects to the login form,
    otherwise renders main page.
    """

    # if user not in session redirect to the login screen
    if session.get("users") is None:
        return redirect("/login")

    return render_template("main.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/check", methods=["POST"])
def check_user():
    """
    If user submits the login form it checks whether particular user data are stored in the database,
    if not renders template with warning about invalid data.
    If user submits the signup form it checks whether username is not taken, hashes the password and stores
    the user data in the database.
    Then it renders the main page.
    """

    # if user is logging in via the /login route
    if request.form.get("login-info"):
        # get user data
        login_info = request.form.get("login-info")
        password = request.form.get("password")
        # if user not in database
        if db.execute("SELECT * FROM users WHERE email = :email OR username = :username",
                      {"email": login_info, "username": login_info}).rowcount == 0:
            return render_template("login.html", message=True)

        # get user's password from the database
        user_data = db.execute("SELECT * FROM users WHERE email = :email OR username = :username",
                               {"email": login_info, "username": login_info}).fetchone()
        # check the provided password
        stored_password = user_data[3]
        if not bcrypt.check_password_hash(stored_password, password):
            return render_template("login.html", message=True)
        db.commit()
    # else - when user is signing up
    else:
        # get user data
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        # check if username not taken
        if db.execute("SELECT * FROM users WHERE username = :username",
                      {"username": username}).rowcount != 0:
            return render_template("signup.html", message=True)

        # hash user's password
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # sign the user up
        db.execute("INSERT INTO users (email, username, password) VALUES \
                   (:email, :username, :password)",
                   {"email": email, "username": username, "password": hashed_password})
        db.commit()

    # store a user in a session and redirect to the main page
    if request.form.get("login-info"):
        session["users"] = login_info
    else:
        session["users"] = username

    return redirect("/")


@app.route("/results", methods=["POST"])
def results():
    """
    Queries the books table with provided data and renders the results page with suiting findings.
    """

    # get the data from the forms
    query = request.form.get("book-query")
    info = request.form.get("book-info")

    # query for a particular criteria
    if query == "All":
        results_list = db.execute("SELECT * FROM books WHERE title ILIKE :title OR \
                                  author ILIKE :author OR isbn ILIKE :isbn",
                                  {"title": '%' + info + '%', "author": '%' + info + '%',
                                   "isbn": '%' + info + '%'}).fetchall()
    elif query == "Title":
        results_list = db.execute("SELECT * FROM books WHERE title ILIKE :title",
                                  {"title": '%' + info + '%'}).fetchall()
    elif query == "Author":
        results_list = db.execute("SELECT * FROM books WHERE author ILIKE :author",
                                  {"author": '%' + info + '%'}).fetchall()
    elif query == "ISBN":
        results_list = db.execute("SELECT * FROM books WHERE isbn ILIKE :isbn",
                                  {"isbn": '%' + info + '%'}).fetchall()
    db.commit()

    return render_template("results.html", results_list=results_list)


@app.route("/book", methods=["GET", "POST"])
def book_page():
    """
    If user is submitting a review for a book, stores that review in the 'reviews' table.
    Queries for book data and reviews associated with the book, makes an API requests to Goodreads
    to get their rating of the book and a request to LibraryThing for book cover.
    Checks whether the user submitted a review for the book - if yes displays a suitable message.
    """

    # get the id of the book from the URL
    id_num = request.args.get("id_num")

    # if user is submitting a review
    if request.form.get("inlineRadioOptions"):
        # submit the review
        rating = int(request.form.get("inlineRadioOptions"))
        user_review = request.form.get("reviewSubmit")
        username = session["users"]

        # store the review in the database
        user = db.execute("SELECT id FROM users WHERE username = :username",
                          {"username": username}).fetchone()
        user_id = user[0]
        db.execute("INSERT INTO reviews (book_id, review, user_id, user_rating)\
                   VALUES (:book_id, :review, :user_id, :user_rating)",
                   {"book_id": id_num, "review": user_review, "user_id": user_id, "user_rating": rating})

    # find the book and reviews in the database
    book_data = db.execute("SELECT * FROM books WHERE id = :id", {"id": id_num}).fetchone()
    reviews = db.execute("SELECT username, user_rating, review FROM users JOIN\
                         reviews ON reviews.user_id = users.id WHERE reviews.book_id = :book_id",
                         {"book_id": id_num}).fetchall()
    db.commit()

    # extract the isbn number
    isbn = book_data[1]
    # make a request to the Goodreads API
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "bZhkuVhGqfuanVIzuFFEOg", "isbns": isbn}).json()
    # make a request to the Library Thing Covers API
    cover_url = f"http://covers.librarything.com/devkey/89b0d45c76e16a28d776b5c37f2ab956/large/isbn/{isbn}"

    def check_review(session, reviews):
        """Check whether the user submitted a review for the particular book."""
        if reviews is None:
            return False
        else:
            for review in reviews:
                if str(review[0]) == session["users"]:
                    return True
        return False

    # set up a flag for checking if user submitted the review
    review_submitted = check_review(session, reviews)

    return render_template("book_page.html", book_data=book_data, res=res, cover_url=cover_url,
                           reviews=reviews, review_submitted=review_submitted)


@app.route("/logout", methods=["POST"])
def logout():
    # remove the user from the current session and redirect to login page
    session.pop("users", None)
    return redirect("/login")


@app.route("/api/<string:isbn>")
def api_request(isbn):
    """
    Queries for books with ISBN number specified in the URL and returns json object with book parameters.
    If does not find suitable data returns 404 error.
    :param isbn: ISBN number of required book
    :return: json with title, author, year, review count and average score; if isbn not found - returns 404 error
    """

    # if isbn not in the database - return 404 error
    if len(db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()) == 0:
        return jsonify({"error": "file not found"}), 404
    db.commit()
    # else - query for the book title, author, year, isbn and rating
    book_data = db.execute("SELECT title, author, year, isbn FROM books WHERE isbn = :isbn",
                           {"isbn": isbn}).fetchone()
    book_ratings = db.execute("SELECT user_rating FROM books JOIN reviews ON reviews.book_id = books.id\
                              WHERE books.isbn = :isbn", {"isbn": isbn}).fetchall()
    db.commit()

    # extract the book data
    title = book_data[0]
    author = book_data[1]
    year = book_data[2]
    isbn = book_data[3]
    review_count = len(book_ratings)

    # calculate the average book score
    overall_score = 0
    for rating in book_ratings:
        overall_score += rating[0]
    try:
        average_score = overall_score/review_count
    except ZeroDivisionError:
        average_score = 0.0

    # return json with data
    return jsonify({
            "title": title,
            "author": author,
            "year": year,
            "isbn": isbn,
            "review_count": review_count,
            "average_score": average_score
            })
