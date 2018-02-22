from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, IntegerField
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'shoppinglist'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#init mysql
mysql = MySQL(app)

@app.route('/')
def index():
	return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

#Single list
@app.route('/lists')
def lists():
	return render_template('lists.html')    

class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min=1,max=50)])
	username = StringField('Username', [validators.Length(min=4,max=25)])
	email = StringField('Email', [validators.Length(min=4,max=50)])
	password = PasswordField('Password', [
		  validators.DataRequired(),
		  validators.EqualTo('confirm', message='Passwords do not match')
		])
	confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET','POST'])
def register():
		form = RegisterForm(request.form)
		if request.method == 'POST' and form.validate():
		    name = form.name.data
		    email = form.email.data
		    username = form.username.data
		    password = sha256_crypt.encrypt(str(form.password.data))

		    cur = mysql.connection.cursor()

		    cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)",(name, email, username, password))

		    mysql.connection.commit()

		    #close connection
		    cur.close()

		    flash('You are now registered and can log in', 'success')

		    return redirect(url_for('login'))
       
		return render_template('register.html', form=form)	 

#User login
@app.route('/login', methods=['GET','POST'])
def login():
	if request.method == 'POST':
		#Get form fields
		username = request.form['username']
		password_candidate = request.form['password']

		#create cursor
		cur = mysql.connection.cursor()

		#get user by username
		result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

		if result > 0:
			#get stored hash
			data = cur.fetchone()
			password = data['password']

			#compare passwords
			if sha256_crypt.verify(password_candidate, password):
				#Passed
				session['logged_in'] = True
				session['username'] = username

				flash('You are now logged in', 'success')
				return redirect(url_for('dashboard'))
			else:
				error = 'Invalid login'
				return render_template('login.html', error=error)
			cur.close()		
		else:
			error = 'Username not found'
			return render_template('login.html', error=error)		

	return render_template('login.html')

#Check if user is logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, please login', 'danger')
			return redirect(url_for('login'))
	return wrap				

#Logout
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))	

#Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
	#create cursor
	cur = mysql.connection.cursor()

	#Get lists
	result = cur.execute("SELECT * FROM lists")

	lists = cur.fetchall()

	if result > 0:
		return render_template('dashboard.html', lists=lists)
	else:
		msg = 'No lists found'	
		return render_template('dashboard.html', msg=msg)
	#close connection
	cur.close()	

#List form class
class ListForm(Form):
	item = StringField('Item', [validators.Length(min=1,max=200)])
	price = IntegerField('Price')
	quantity = StringField('Quantity', [validators.Length(max=200)])	

#Add list
@app.route('/add_list',methods=['GET','POST'])
@is_logged_in
def add_list():
	form = ListForm(request.form)
	if request.method == 'POST' and form.validate():
		item = form.item.data
		price = form.price.data
		quantity = form.quantity.data 

		#create cursor
		cur = mysql.connection.cursor()

		cur.execute("INSERT INTO lists(item, price, quantity) VALUES(%s, %s, %s)",(item, price, quantity))

		#Commit to DB
		mysql.connection.commit()

		#close connection
		cur.close()

		flash('Shopping List created', 'success')

		return redirect(url_for('dashboard'))

	return render_template('add_list.html', form=form)	

#Edit list
@app.route('/edit_list/<string:id>',methods=['GET','POST'])
@is_logged_in
def edit_list(id):

	#create cursor
	cur = mysql.connection.cursor()

	#Get list by id
	result = cur.execute("SELECT * FROM lists WHERE id=%s", [id])

	list = cur.fetchone()

	form = ListForm(request.form)

	#Populate list form fields
	form.item.data = list['item']
	form.price.data = list['price']
	form.quantity.data = list['quantity']

	if request.method == 'POST' and form.validate():
		item = request.form['item']
		price = request.form['price']
		quantity = request.form['quantity'] 

		#create cursor
		cur = mysql.connection.cursor()

		cur.execute("UPDATE lists SET item=%s, price=%s, quantity=%s WHERE id=%s",(item,price,quantity,id))

		#Commit to DB
		mysql.connection.commit()

		#close connection
		cur.close()

		flash('Shopping List updated', 'success')

		return redirect(url_for('dashboard'))

	return render_template('edit_list.html', form=form)	

#Delete list
@app.route('/delete_list/<string:id>', methods=['POST'])
@is_logged_in
def delete_list(id):
	#create cursor
	cur = mysql.connection.cursor()

	cur.execute("DELETE FROM lists WHERE id=%s", [id])

	mysql.connection.commit()

	cur.close()

	flash('Shopping List deleted','success')

	return redirect(url_for('dashboard'))				   	


if __name__ == '__main__':
	app.secret_key = '123456'
	app.run(debug=True)