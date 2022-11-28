import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
#from tabulate import tabulate

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    portfolio = db.execute("SELECT * FROM purchases WHERE id=:id AND shares > 0", id=session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    cashhh = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])[0]['cash']

    tot = cashhh
    for symbol in portfolio:
        price = lookup(symbol['symbol'])['price']
        total = symbol['shares'] * price
        symbol.update({'price': price})
        symbol.update({'total': total})
        tot = tot + total

    return render_template("index.html", portfolio=portfolio, cash=cash, tot=tot)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        # if it is empty
        if not request.form.get("symbol"):
            return apology("Enter a valid symbol", 400)
        # if stock ticker doesn't exist
        if not lookup(request.form.get("symbol")):
            return apology("Not a valid ticker symbol")
        # check if non numeric
        if request.form.get("shares").isdigit() == False:
            return apology("Enter a number of shares to purchase", 400)
        # check if negative
        if int(request.form.get("shares")) <= 0:
            return apology("Enter a positive amount of shares to buy", 400)
        if request.form.get("shares").isdecimal() == False:
            return apology("Enter a whole number of shares", 400)

        thestock = lookup(request.form.get("symbol"))
        thestockname = thestock["name"]
        thestockticker = thestock["symbol"]
        thestockprice = thestock["price"]

        usercash = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
        requestedshares = request.form.get("shares")

        totalcost = float(requestedshares) * float(thestockprice)
        if totalcost > float(usercash[0]["cash"]):
            return apology("Insufficient Funds", 400)

        # how much cash the user will have after the transaction
        newcash = usercash[0]["cash"] - totalcost
        db.execute("UPDATE users SET cash=:newcash WHERE id=:id", id=session["user_id"], newcash=newcash)

        datetimeobject = datetime.datetime.now()
        db.execute("INSERT INTO purchases (id, symbol, name, shares, price, total) VALUES (:id, :symbol, :name, :shares, :price, :total)",
                   id=session["user_id"], symbol=thestockticker, name=thestockname, shares=requestedshares, price=thestockprice, total=totalcost)
        db.execute("INSERT INTO history (bs, symbol, price, shares, datetime, id) VALUES (:bs, :symbol, :price, :shares, :datetimeee, :id)",
                   bs="Buy", symbol=thestockticker, price=thestockprice, shares=requestedshares, datetimeee=datetimeobject, id=session["user_id"])
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    history = db.execute("SELECT * FROM history WHERE id=:id", id=session["user_id"])

    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        # if it is empty
        if not request.form.get("symbol"):
            return apology("Enter a valid symbol", 400)
        # if stock ticker doesn't exist
        if not lookup(request.form.get("symbol")):
            return apology("Not a valid ticker symbol")
        else:
            thestock = lookup(request.form.get("symbol"))
            thestockname = thestock["name"]
            thestockticker = thestock["symbol"]
            thestockprice = thestock["price"]
        return render_template("quoted.html", thestockname=thestockname, thestockprice=usd(thestockprice), thestockticker=thestockticker)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif not request.form.get("confirmation"):
            return apology("please confirm the passowrd", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match")

        # password into memory
        username = request.form.get("username")
        userrepeatcheck = db.execute("SELECT username FROM users WHERE username = :username", username=username)
        if userrepeatcheck:
            return apology("Username already taken")

        else:
            hash = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                              username=username, hash=generate_password_hash(request.form.get("password")))

        # Remember which user has logged in
            session["user_id"] = hash

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":

        # if user doesn't enter a symbol
        if not request.form.get("symbol"):
            return apology("Enter a symbol", 400)
        # if stock ticker doesn't exist
        if not lookup(request.form.get("symbol")):
            return apology("Not a valid ticker symbol", 400)
        # make sure number of shares is a number
        if request.form.get("shares").isdigit() == False:
            return apology("Enter a number of shares to sell", 400)
        # make sure shares entered is a positive amount
        if int(request.form.get("shares")) <= 0:
            return apology("Enter a positive amount of shares to sell", 400)

        thestock = lookup(request.form.get("symbol"))
        thestockname = thestock["name"]
        thestockticker = thestock["symbol"]
        thestockprice = thestock["price"]
        l = 10

        stocks = db.execute("SELECT symbol FROM purchases WHERE id=:id AND symbol=:symbol",
                            id=session["user_id"], symbol=thestockticker)
        drop = db.execute("SELECT symbol FROM purchases WHERE id=:id", id=session["user_id"])

        numstocks = db.execute("SELECT shares FROM purchases WHERE id=:id AND symbol=:symbol",
                               id=session["user_id"], symbol=thestockticker)
        st = lookup(request.form.get("symbol"))
        cost = int(request.form.get("shares")) * st["price"]
        pr = st["price"]
        s = int(request.form.get("shares"))

        if len(stocks) == 0:
            return apology("Stock not in your portfolio", 400)

        elif str(numstocks[0]) >= str(request.form.get("shares")):
            datetimeobjecttt = datetime.datetime.now()
            db.execute("UPDATE users SET cash=cash+:cost WHERE id=:id", cost=cost, id=session["user_id"])
            db.execute("UPDATE purchases SET shares=shares-:request WHERE id=:id AND symbol=:symbol",
                       request=s, id=session["user_id"], symbol=thestockticker)
            db.execute("INSERT INTO history (bs, symbol, price, shares, datetime, id) VALUES (:bs, :symbol, :price, :shares, :datetimeee, :id)",
                       bs="Sell", symbol=thestockticker, price=thestockprice, shares=s, datetimeee=datetimeobjecttt, id=session["user_id"])

            return redirect("/")
        else:
            return apology("Error", 400)

    else:
        drop = db.execute("SELECT symbol FROM purchases WHERE id=:id", id=session["user_id"])
        return render_template("sell.html", drop=drop)