from website.models import Room, db
from website.seed_rooms import seed_rooms

def test_seed_rooms(app):
    assert Room.query.count() == 0

    seed_rooms()

    rooms = Room.query.all()
    assert len(rooms) == 10
    assert any(r.building_name == "Lovejoy" and r.room_number == 100 for r in rooms)
    assert any(r.building_name == "Gordon" and r.room_number == 2 for r in rooms)

def test_seed_existing_rooms(app):
    r = Room(building_name="TestBuilding", room_number=1, capacity=10)
    db.session.add(r)
    db.session.commit()

    seed_rooms()

    assert Room.query.filter_by(building_name="TestBuilding", room_number=1).first() is not None

    assert Room.query.count() == 1