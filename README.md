__Books’up__ is a CRUD-functionality book review web application, based on [CS50 Web Programming Assignment](https://docs.cs50.net/web/2018/x/projects/1/project1.html). Users are able to register to the website and then log in using provided username and password. Once logged in users are able to search for books, leave review for invidual books, and browse reviews submitted by other people.
The application uses a third party APIs: one from Goodreads website, to get more ratings from a broader audience, and the second one from LibraryThing, supplying images of book covers.
The website provides also an API for users to programmatically query for book details and reviews.

Technologies used: __Flask__, __SQLAlchemy__, __PostgreSQL__, __HTML5__, __CSS3__.

### Model
Application uses a relational PostgreSQL database, hosted on Heroku, consisting of three tables:
* __users__ - stores the information about users that created the account on the website – id, email, username and hashed password,
* __books__ - stores books informations – id, isbn, title, author, year,
* __reviews__ - stores reviews for an invidual book – id, book_id (references books table), review, user_id (references users table), user_rating.

### View
The website consists of four substantial web pages:
* __signup.html__/__login.html__- forms to create an account and log in to the app,
* __main.html__ - the main web page, contains the top navbar with home and log off buttons and a three-part form to search a book (select field for picking a criteria of searching – Title, Author, Isbn; input field for typing in data; submit button),
* __results.html__ - the web page displaying books fulfilling the conditions specified in the searching form; shows a list of book records with book cover image, title, year and ISBN number,
* __book_page.html__ - an individual book page, displays enlarged book cover, book data, a radio form to rate the book on the scale 1 to 5, a textarea and submit button to create a review and the list of reviews submitted by other users. If the user already reviewed the book he can no longer submit a review.

### Controller
* __application.py__ - performs server logic of the application, including listening to requests, creating and assigning sessions, checking users, quering for book informations, making API requests and creating own API for other people to use programmatically.
---
Additional files:
- requirements.txt – required Python packages,
- books.csv – books to be uploaded to the database,
- import.py – logic for opening the books.csv file and inserting the data into the books table.