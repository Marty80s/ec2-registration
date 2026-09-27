import sys
sys.path.insert(0, '/var/www/ec2-registration')
from app import create_app
application = create_app()
