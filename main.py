# coding: utf-8
import flask
from functools import wraps
#sqlalchemy
from flask_sqlalchemy import SQLAlchemy
#custom config
import config
#datetime
from datetime import datetime as dt
import os.path as op
from json import dumps as json_dumps
#from datetime import date, timedelta
#crypt for user's password
from flask_bcrypt import Bcrypt
#os for file processing
import os
import random
from json import dumps as json_dumps
#https connection
#from OpenSSL import SSL
#flask_admin
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.form.upload import FileUploadField, ImageUploadField

from flask_ckeditor import CKEditor, CKEditorField

from werkzeug.utils import secure_filename
from wtforms.fields import TextField


app = flask.Flask(__name__)

bcrypt = Bcrypt(app)
app.secret_key = config.secret_key

ckeditor = CKEditor(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + config.db_file
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['THUMBNAIL_FOLDER'] = config.THUMBNAIL_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 80 * 1024 * 1024 #80mb max
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
db = SQLAlchemy(app)

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#------------------------<databases classes>------------------------------

class Setting(db.Model):

	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	name = db.Column(db.String())
	value = db.Column(db.String())

	def __repr__(self):
		return self.name

class User(db.Model):

	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	username = db.Column(db.String())
	email = db.Column(db.String())
	password = db.Column(db.String())
	privilege_id = db.Column(db.Integer, db.ForeignKey("privilege.id"), nullable=False, default = 3)

	def __repr__(self):
		return self.username

class Privilege(db.Model):

	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	name = db.Column(db.String())
	users = db.relationship("User", backref="privelege")

	def __repr__(self):
		return self.name

class Good(db.Model):

	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	title = db.Column(db.String(), nullable=False)
	details = db.Column(db.String())
	price = db.Column(db.Integer)
	img = db.Column(db.String())
	weight = db.Column(db.String())
	category_id = db.Column(db.Integer, db.ForeignKey('category.id'),
		nullable=False)
	orders = db.relationship('Orders', backref='good', lazy=True)
	show = db.Column(db.Boolean)

	def __repr__(self):
		return self.title

class Category(db.Model):

	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	name = db.Column(db.String())
	goods = db.relationship('Good', backref='category', lazy=True)
	has_pita = db.Column(db.Boolean)

	def __repr__(self):
		return self.name

class Page(db.Model):

	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	name = db.Column(db.String())
	content = db.Column(db.String())

	def __repr__(self):
		return self.name

class Pita(db.Model):

	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	name = db.Column(db.String())
	price = db.Column(db.Integer)
	orders = db.relationship('Orders', backref='pita_type', lazy=True)

	def __repr__(self):
		return self.name

class Order(db.Model):

	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	customer_id = db.Column(db.String())
	goods = db.relationship('Orders', backref='order', lazy=True)
	address = db.Column(db.String())
	comment = db.Column(db.String())
	phone = db.Column(db.String())

	def __repr__(self):
		return self.address

class Orders(db.Model):
	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
	good_id = db.Column(db.Integer, db.ForeignKey('good.id'),
		nullable=False)
	amount = db.Column(db.Integer)
	pita_id = db.Column(db.Integer, db.ForeignKey('pita.id'))

	def __repr__(self):
		if self.pita_type:
			return str(self.good) + ' ' + str(self.amount) + 'шт. Лаваш: ' + str(self.pita_type)
		else:
			return str(self.good) + ' ' + str(self.amount) + 'шт. Лаваш: ' + str(self.pita_type) 


db.create_all()

#------------------/database classes/---------------------------

#------------------<flask_admin>--------------------------------

#restict access to /admin index
class MyAdminIndexView(AdminIndexView):

	def is_visible(self):
		return False

def prefix_name(obj, file_data):
	hash = random.getrandbits(128)
	ext = file_data.filename.split('.')[-1]
	path = '%s.%s' % (hash, ext)
	return path

def thumb_name(file_data):
	#name = file_data.split("/")
	return os.path.join('thumbnails', file_data)

#list of users in admin
class DefView(ModelView):
	column_display_pk = True

	form_overrides = {
		'img': ImageUploadField
	}

	form_args = {
		'img': {
			'label': 'Изображение',
			'base_path': 'static',
			'allow_overwrite': True,
			'namegen': prefix_name,
			'max_size': (700,560,True),
			'thumbnail_size': (256,256, True),
			'thumbgen' : thumb_name
		}
	}

class StorageAdminModel(ModelView):
	form_extra_fields = {
		'file': FileUploadField('file', base_path = app.config['UPLOAD_FOLDER'], namegen = prefix_name)
	}

	def on_model_change(self, form, Setting, is_created=False):
		if not form.value.data:
			Setting.value = os.path.join(app.config['UPLOAD_FOLDER'], form.file.data.filename)
 
class PageAdminMode(ModelView):
	form_extra_fields = {
		'temp_field': TextField('Загрузить файл')
	}

	form_overrides = dict(content=CKEditorField)

	create_template = 'admin_edit.html'
	edit_template = 'admin_edit.html'


#initialize admin views
admin = Admin(app, name='Панель управления', template_mode='bootstrap3', index_view=MyAdminIndexView(), url='/')
admin.add_view(StorageAdminModel(Setting, db.session, 'Настройки', url='/admin/settings'))
admin.add_view(DefView(User, db.session, 'Пользователи', url='/admin/user'))
admin.add_view(DefView(Good, db.session, 'Товары', url='/admin/goods'))
admin.add_view(DefView(Category, db.session, 'Категории', url='/admin/categories'))
admin.add_view(DefView(Pita, db.session, 'Лаваш', url='/admin/pitas'))
admin.add_view(DefView(Order, db.session, 'Заказы', url='/admin/orders'))
admin.add_view(DefView(Orders, db.session, 'Заказы_test', url='/admin/order_test'))
admin.add_view(PageAdminMode(Page, db.session, 'Страницы', url='/admin/pages'))

#---------------------/flask_admin/---------------------

def get_settings():
	as_dict = {}
	for i in Setting.query.all():
		as_dict[i.name] = i.value
	
	return as_dict

def register_customer():
	if 'user_id' not in flask.session:
		flask.session['user_id'] = random.getrandbits(128)

def get_cart_amount():

	amount = 0

	if 'goods_in_cart' in flask.session: #if has cart in cookies
		for good in flask.session['goods_in_cart']:
			try:
				amount += good['amount']
			except:
				pass

	return amount

@app.route('/save_image', methods=["GET","POST"])
def save_image():
	if 'files[]' not in flask.request.files:
		resp = flask.jsonify({'message' : 'No file part in the request'})
		resp.status_code = 400
		return resp
	
	files = flask.request.files.getlist('files[]')
	
	errors = {}
	success = False
	filenames = []
	
	for file in files:
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			success = True
			filenames.append('/' + os.path.join(app.config['UPLOAD_FOLDER'], filename))
		else:
			errors[file.filename] = 'File type is not allowed'
	
	if success and errors:
		errors['message'] = 'File(s) successfully uploaded'
		errors['filenames'] = filenames
		resp = flask.jsonify(errors)
		resp.status_code = 206
		return resp
	if success:
		resp = flask.jsonify({'message' : 'Files successfully uploaded', 'filenames':filenames})
		resp.status_code = 201
		return resp
	else:
		resp = flask.jsonify(errors)
		resp.status_code = 400
		return resp


@app.route('/update_good_cart', methods=["POST"])
def update_good_cart():

	goods = []
	summ = 0

	update_good = flask.request.json

	if 'goods_in_cart' in flask.session:
		for good in flask.session['goods_in_cart']:
			good_model = Good.query.get(good['good_id'])
			if update_good['good_id'] == good['good_id']:
				if good_model.category.has_pita:
					update_good['price'] = good_model.price * int(update_good['amount']) + Pita.query.get(update_good['pita']).price
				else:
					update_good['price'] = good_model.price * int(update_good['amount'])

				good = update_good
			goods.append(good)

			summ += good_model.price * int(good['amount'])

	#update_good['price'] = Good.query.get(update_good['good_id']).price + Pita.query.get(update_good['pita']).price

	flask.session['goods_in_cart'] = goods

	return json_dumps({'success': True, 'cart': flask.session['goods_in_cart'], 'updated_good':update_good, 'summ':summ}), 200, {'ContentType':'application/json'} 



@app.route('/add_good_cart', methods=["POST"])
def add_good_cart():

	goods = []
	temp = []

	new_good = flask.request.json

	if 'goods_in_cart' in flask.session: #if has cart in cookies
		for good in flask.session['goods_in_cart']: #get every item from cookie's cart
			if new_good['good_id'] == good['good_id']: #and if this item equals to new item
				good['amount'] += new_good['amount'] #just add amount but don't create new item
				good['price'] = good['amount'] * Good.query.get(good['good_id']).price
			goods.append(good) #and add to list of goods
			temp.append(good['good_id']) #add id to temp list of id's
			#this needed to check that there's element in cart
			#and if it's not add it

		try:
			temp.index(new_good['good_id']) #trying to find new element in cart
		except:
			goods.append(new_good) #if it's not - add it
	else: #if cart is empty then add first element
		goods.append(new_good)

	flask.session['goods_in_cart'] = goods #update cart in cookies

	return json_dumps({'success': True, 'cart': flask.session['goods_in_cart']}), 200, {'ContentType':'application/json'} 

@app.route("/", methods=["GET"])
def index():

	register_customer()
	
	return flask.render_template("index.html", 
		categories = Category.query.all(), 
		settings = get_settings(), 
		pages = Page.query.all(),
		cart_amount = get_cart_amount())

@app.route('/pages/<page_id>', methods=["GET","POST"])
def pages(page_id):

	return flask.render_template("page.html", 
		categories = Category.query.all(), 
		settings = get_settings(), 
		page = Page.query.get(page_id),
		pages = Page.query.all(),
		cart_amount = get_cart_amount())

@app.route('/good/<good_id>', methods=["GET","POST"])
def goods(good_id):

	register_customer()

	return flask.render_template("good.html", 
		categories = Category.query.all(), 
		settings = get_settings(), 
		good = Good.query.get(good_id),
		pages = Page.query.all(),
		cart_amount = get_cart_amount())

@app.route('/cart', methods=["GET","POST"])
def cart():

	register_customer()

	order_list = []
	summ = 0

	if 'goods_in_cart' in flask.session:
		for good in flask.session['goods_in_cart']:
			good_model = Good.query.get(good['good_id'])
			if Good.query.get(good['good_id']).category.has_pita:
				price = Good.query.get(good['good_id']).price * int(good['amount']) + Pita.query.get(good['pita']).price
			else:
				price = Good.query.get(good['good_id']).price * int(good['amount'])

			order_list.append({'good':good_model,
				'amount':good['amount'],
				'pita':good['pita'],
				'price': price})
			try:
				summ += good_model.price * int(good['amount'])
			except:
				pass


	return flask.render_template("cart.html", 
		categories = Category.query.all(), 
		settings = get_settings(), 
		cart = order_list,
		pitas = Pita.query.all(),
		pages = Page.query.all(),
		cart_amount = get_cart_amount(),
		summ = summ)

@app.route('/pop_cart_good', methods=["POST"])
def pop_cart_good():
	good_id = flask.request.args.get("id")
	goods = []

	if 'goods_in_cart' in flask.session:
		for good in flask.session['goods_in_cart']:
			if str(good["good_id"]) != str(good_id):
				goods.append(good)

	flask.session['goods_in_cart'] = goods
	return flask.redirect(flask.url_for("cart"))

@app.route('/confirm_order', methods=["POST"])
def confirm_order():
	f = flask.request.form.to_dict(flat=False)

	new_order = Order(address = f['address'][0], phone = f['phone_number'][0], comment = f['comment'][0])
	db.session.add(new_order)
	if 'goods_in_cart' in flask.session:
		print(flask.session['goods_in_cart'])
		for good in flask.session['goods_in_cart']:
			if good['pita']:
				good_order = Orders(good_id = int(good['good_id']), amount = int(good['amount']), pita_id = good['pita'])
			else:
				good_order = Orders(good_id = int(good['good_id']), amount = int(good['amount']))

			new_order.goods.append(good_order)
			db.session.add(good_order)

	db.session.commit()

	flask.session.pop('goods_in_cart')
	return flask.redirect(flask.url_for("index"))


if __name__ == "__main__":
	app.run(host=config.host, port=config.port)#, ssl_context='adhoc')