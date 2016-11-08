from flask import (Flask, render_template, redirect, request, flash,
                   session)
from jinja2 import StrictUndefined
from flask_debugtoolbar import DebugToolbarExtension
from model import (connect_to_db, db, Product, Recipe, Tag, Product_Tag, Customer,
                   Customer_Recipe, Pickup, Delivery, Dietary_Restriction,
                   Customer_Restriction, Order, Icon, Delivery_Quantity,
                   Order_Quantity)
from passlib.hash import pbkdf2_sha256
from math import floor
import api
import functions

app = Flask(__name__)

#Required to use Flask sessions, Debug toolbar
app.secret_key = "daksfhausdfskgbxpuseswlduc"

#For debugging - see Jinja fails
app.jinja_env.undefined = StrictUndefined
app.jinja_env.auto_reload = True


@app.route('/')
def show_home():
    """Display homepage"""

    return render_template("index.html")


@app.route('/login')  # currently using modal window instead of route...
def show_login():
    """Show login form"""

    pass


@app.route('/login', methods=['POST'])
def process_login():
    """Process login data. Add user_id to session"""

    email = request.form.get('email')
    password = request.form.get('password')

    user = db.session.query(Customer).filter(Customer.email == email).first()

    if user and pbkdf2_sha256.verify(password, user.password_hash):

        session['email'] = email

        flash("Login successful!")

        return "Success"

    else:

        return "Fail"


@app.route('/logout')
def process_logout():
    """Log user out, redirect to /products"""

    del session['email']

    flash("You have been logged out.")

    return redirect("/products")


@app.route('/register')
def show_register():
    """Show registration form"""

    return render_template("register.html")


@app.route('/register', methods=['POST'])
def process_registration():
    """Process user registration"""

    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")
    password = request.form.get("password")
    password = pbkdf2_sha256.encrypt(password, rounds=20000, salt_size=16)
    street_address = request.form.get("address")
    zipcode = request.form.get("zipcode")
    state = request.form.get("state")
    phone = request.form.get("phone")

    user = Customer(first_name=first_name, last_name=last_name, email=email,
                    password_hash=password, street_address=street_address,
                    zipcode=zipcode, state=state, phone=phone)

    db.session.add(user)
    db.session.commit()
    flash("Registration successful! Welcome to Farm to Front Door.")
    session['email'] = email

    return redirect("/products")


@app.route('/products')
def show_products():
    """Query database for product list & display results"""

    products = db.session.query(Product).all()

    return render_template("products.html", products=products)


@app.route('/products', methods=["POST"])
def add_products_to_cart():
    """Add product to cart from button click"""

    product_id = int(request.form.get("productId"))  # this can be wrapped in a func to DRY up code
    product = Product.query.get(product_id)
    session["cart"] = session.get("cart", {})
    # session["cart_total"] = session.get("cart_total", 0) + product.price
    session["cart"][product_id] = session["cart"].get(product_id, 0) + 1

    cart = session["cart"]
    print cart

    return redirect("/products")


@app.route('/products/<int:product_id>')  # takes product_id as an INTEGER
def show_product_page(product_id):
    """Query database for product info and display results"""

    product = Product.query.get(product_id)

    return render_template("product_page.html", product=product)


@app.route('/products/<int:product_id>', methods=["POST"])  # takes product_id as an INTEGER
def add_product_to_cart(product_id):
    """Add product to cart from button click on prod page"""

    product_id = int(request.form.get("productId"))
    product = Product.query.get(product_id)
    session["cart"] = session.get("cart", {})
    # session["cart_total"] = session.get("cart_total", 0) + product.price
    session["cart"][product_id] = session["cart"].get(product_id, 0) + 1

    cart = session["cart"]
    print cart

    return redirect('/products/' + str(product_id))


@app.route('/cart')
def show_cart():
    """Query session for cart contents and display results"""

    # cart_weight = {'lb': 0,
    #                'oz': 0}

    # session["cart_total"] = 0
    recipes = []
    cart_weight = 0

    if 'cart' in session:
        cart = Product.query.filter(Product.product_id.in_(session['cart'].keys())).all()
        print session['cart']

        cart_weight = functions.get_cart_weight(cart)
        functions.get_cart_total(cart)

        # #calculate weight of cart
        # for item in cart:
        #     if item.unit in cart_weight:
        #         cart_weight[item.unit] += float(item.weight) * float(session["cart"][item.product_id])
        #     elif item.per_unit and item.price_per:
        #         cart_weight[item.per_unit] += float(item.price) / float(item.price_per) * float(session["cart"][item.product_id])
        #     else:
        #         cart_weight["fudged"] = True

        # #calculate total price of cart
        # for item in cart:
        #     session["cart_total"] += item.price * session['cart'][item.product_id]

        # #smooth over decimal lbs and round up ounces if necessary
        # if cart_weight['lb'] != floor(cart_weight['lb']):
        #     ozes = (cart_weight['lb'] - floor(cart_weight['lb'])) * 16.0
        #     cart_weight['lb'] = floor(cart_weight['lb'])
        #     cart_weight['oz'] += ozes
        # if cart_weight['oz'] > 16:
        #     cart_weight['lb'] += floor(cart_weight['oz'] / 16)
        #     cart_weight['oz'] = cart_weight['oz'] % 16

        #suggest recipes
        product_names = api.split_params([item.name for item in cart])
        recipes = api.get_recipes(product_names)

    else:
        cart = []

    return render_template("cart.html", cart=cart, cart_weight=cart_weight, recipes=recipes)


@app.route('/cart', methods=['POST'])
def update_cart():
    """Update cart quantites"""

    print "pass 1 **************************************"
    product_id = int(request.form.get("product_id"))
    print "product id is ", product_id
    qty = int(request.form.get("qty"))
    print "qty is ", qty

    #REMINDER: calculate price on page.
    session['cart'][product_id] = qty

    session.modified = True
    print session['cart']

    return "Success"


@app.route('/delete')
def delete_item():
    """Delete item from shopping cart"""

    product_id = int(request.args.get('id'))
    print product_id

    del session['cart'][product_id]
    session.modified = True

    return redirect('/cart')


@app.route('/checkout')
def check_out():
    """Check out"""

    cart = Product.query.filter(Product.product_id.in_(session['cart'].keys())).all()
    functions.get_cart_total(cart)

    return render_template("checkout.html", cart=cart)


@app.route('/checkout', methods=['POST'])
def process_payment():
    """Process payment"""

    cart = Product.query.filter(Product.product_id.in_(session['cart'].keys())).all()
    functions.get_cart_total(cart)

    api.pay_for_cart()

    return render_template("success.html")


@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 page"""

    return render_template('404.html'), 404


if __name__ == "__main__":
    # Change app.debug to False before launch
    app.debug = True
    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    app.run(host="0.0.0.0")
