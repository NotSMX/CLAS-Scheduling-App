from website import db
from . import website
from .models import Room

def seed_rooms():
    with website.app_context():
        # Check if rooms already exist
        if Room.query.first():
            print("Rooms already exist in database")
            return
        
        # Add sample rooms
        rooms = [
            Room(building_name="Lovejoy", room_number=100, capacity=30, special_features="Projector, Whiteboard"),
            Room(building_name="Lovejoy", room_number=101, capacity=25, special_features="Projector"),
            Room(building_name="Lovejoy", room_number=215, capacity=40, special_features="Smart Board, Large Screen"),
            
            Room(building_name="Diamond", room_number=145, capacity=35, special_features="Lab Equipment"),
            Room(building_name="Diamond", room_number=122, capacity=20, special_features="Microscopes"),
            Room(building_name="Diamond", room_number=230, capacity=50, special_features="Auditorium Style"),
            
            Room(building_name="Keyes", room_number=105, capacity=30, special_features="Computer Lab"),
            Room(building_name="Keyes", room_number=301, capacity=45, special_features="Presentation Equipment"),
            
            Room(building_name="Gordon", room_number=1, capacity=100, special_features="Performance Space, Stage"),
            Room(building_name="Gordon", room_number=2, capacity=60, special_features="Recital Hall"),
        ]
        
        for room in rooms:
            db.session.add(room)
        
        db.session.commit()
        print(f"Successfully added {len(rooms)} rooms to the database!")

if __name__ == "__main__":
    seed_rooms()