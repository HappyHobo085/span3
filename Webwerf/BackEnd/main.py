#backend python kode wat die API calls en data van die frontend javascript kode roep

#Ek persoonlik dink ons moet 'n python file skep vir elke web bladsy, dit gaan dit meer effektief maak en makliker maak
#Soos bv. login.py, index.py, events.py, koshuis.py, sub_stelsel.py
#En dan 'n main.py wat al die API calls en data van die frontend javascript kode roep

from flask import Flask
from config import Config
from database import db, migrate
import models  # belangrik — modelle moet geïmporteer word

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate.init_app(app, db)

if __name__ == '__main__':
    app.run(debug=True)