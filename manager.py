from flask_migrate import MigrateCommand
from flask_script import Manager

from app import app

manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == "__main__":
    manager.run()

################################
# flask migrate CLI:           #
# python manager.py db init    #
# python manager.py db migrate #
# python manager.py db upgrade #
# python manager.py db --help  #
#############################################################################################
# python manager.py db init && python manager.py db migrate && python manager.py db upgrade #
#############################################################################################

