import sqlite3

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler_STDOUT = logging.FileHandler('STDOUT')
file_handler_STDOUT.setLevel(logging.DEBUG)

file_handler_STDERR = logging.FileHandler('STDERR')
file_handler_STDERR.setLevel(logging.ERROR)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler_STDOUT.setFormatter(formatter)
file_handler_STDERR.setFormatter(formatter)

logger.addHandler(file_handler_STDOUT)
logger.addHandler(file_handler_STDERR)

# Global variable to keep track of the number of database connections
db_connection_count = 0

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    try:
        connection = sqlite3.connect('database.db')
        connection.row_factory = sqlite3.Row
        global db_connection_count
        db_connection_count += 1
        return connection
    except Exception as e:
        logger.error('Error connecting to database: ' + str(e))
        return None

# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    return post

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

# Define the main route of the web application 
@app.route('/')
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    logger.info('The homepage has been retrieved.')
    return render_template('index.html', posts=posts)

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    
    if post is None:
      logger.error('Post not found!')
      return render_template('404.html'), 404
    else:
      logger.info('Article "' + post['title'] + '" retrieved!')
      return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    logger.info('"About Us" page is retrieved')
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()

            logger.info('Article "' + title + '" created!')
            
            return redirect(url_for('index'))

    return render_template('create.html')

@app.route('/healthz')
def status():

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts';")
        table_exists = cursor.fetchone()
        if table_exists:
            response = app.response_class(
                response=json.dumps({"result":"OK - healthy"}),
                status=200,
                mimetype='application/json'
            )
            logger.info('Status request successful')
        else:
            response = app.response_class(
                response=json.dumps({"result":"ERROR - unhealthy"}),
                status=500,
                mimetype='application/json'
            )
            logger.info('Status request failed: posts table does not exist')
            
        cursor.close()
        connection.close()
    except Exception as e:
        response = app.response_class(
            response=json.dumps({"result":"ERROR - unhealthy"}),
            status=500,
            mimetype='application/json'
        )
        logger.error('Status request failed: ' + str(e))


    
    return response

@app.route('/metrics')
def metrics():

    connection = get_db_connection()

    post_count = connection.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    connection.close()
    
    response = app.response_class(
            response=json.dumps({"db_connection_count": db_connection_count, "post_count": post_count}),
            status=200,
            mimetype='application/json'
    )
    logger.info('Metrics request successfull')
    return response

# start the application on port 3111
if __name__ == "__main__":
   app.run(host='0.0.0.0', port='3111')
