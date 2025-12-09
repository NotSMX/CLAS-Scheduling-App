from collections import defaultdict
from models import Session, Event, Room, db
from datetime import datetime, time, timedelta
from sqlalchemy import and_, cast, String

def build_schedule_suggestions(events):
    """
    Group events by day and room, and return a light-weight
    structure for the schedule page.
    """
    schedule = defaultdict(lambda: defaultdict(list))
    for ev in events:
        day = ev.day or "Unscheduled"
        room = ev.room_id or "TBD Room"
        schedule[day][room].append(ev)
    # Turn into a sorted list of day blocks for template
    day_blocks = []
    for day in sorted(schedule.keys()):
        room_blocks = []
        for room in sorted(schedule[day].keys()):
            room_events = sorted(
                schedule[day][room],
                key=lambda e: (e.start_time or "", e.session_title or ""),
            )
            room_blocks.append(
                {
                    "room": room,
                    "events": room_events,
                }
            )
        day_blocks.append(
            {
                "day": day,
                "rooms": room_blocks,
            }
        )
    return day_blocks

class Scheduler:
    def __init__(self):
        self.time_slots = self._generate_time_slots()
        
    def _generate_time_slots(self):
        """Generate 15-minute time slots from 9 AM to 5 PM"""
        slots = []
        start = datetime.strptime("09:00", "%H:%M")
        end = datetime.strptime("17:00", "%H:%M")
        current = start
        
        while current < end:
            slots.append(current.time())
            current += timedelta(minutes=15)
        
        return slots
    
    def _get_room_conflicts(self, room_id, start_time, end_time, exclude_session_id=None):
        """
        Return a list of conflicting APPROVED sessions for this room & time.
        """
        query = (
            Session.query
            .join(Event)
            .filter(
                Session.room_id == room_id,
                Event.status == 'approved',           
                Session.start_time < end_time,
                Session.end_time > start_time
            )
        )

        if exclude_session_id:
            query = query.filter(Session.id != exclude_session_id)

        return query.all()


    def _check_room_availability(self, room_id, start_time, end_time, exclude_session_id=None):
        """
        Backwards compatible – still returns True/False.
        """
        conflicts = self._get_room_conflicts(
            room_id=room_id,
            start_time=start_time,
            end_time=end_time,
            exclude_session_id=exclude_session_id
        )
        return len(conflicts) == 0

    
    def _find_suitable_rooms(self, event, start_time, end_time):
        """Find all suitable rooms based on event requirements"""
        suitable_rooms = []
        
        # Try to honor room request first
        if event.room_request:
            requested_rooms = Room.query.filter(
                (Room.building_name.ilike(f"%{event.room_request}%")) |
                (cast(Room.room_number, String).ilike(f"%{event.room_request}%"))
            ).all()
            
            for room in requested_rooms:
                if room.capacity >= event.num_students:
                    if self._check_room_availability(room.id, start_time, end_time):
                        suitable_rooms.append(room)
        
        # Find any suitable rooms
        all_suitable_rooms = Room.query.filter(
            Room.capacity >= event.num_students
        ).order_by(Room.capacity).all()
        
        for room in all_suitable_rooms:
            if room not in suitable_rooms:
                if self._check_room_availability(room.id, start_time, end_time):
                    suitable_rooms.append(room)
        
        return suitable_rooms
    
    def generate_schedule_options(self, event_id, max_options=5):
        """Generate multiple schedule options for an event"""
        event = Event.query.get(event_id)
        if not event:
            return []
        
        if event.status != "submitted":
            return []
        
        duration_minutes = event.session_length
        options = []
        
        # Try to find multiple time slots
        for slot in self.time_slots:
            if len(options) >= max_options:
                break
                
            start_datetime = datetime.combine(datetime.today(), slot)
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            end_time = end_datetime.time()
            
            # Check if end time is within working hours
            if end_time > time(17, 0):
                continue
            
            # Find suitable rooms
            rooms = self._find_suitable_rooms(event, slot, end_time)
            
            for room in rooms[:3]:  # Limit to 3 rooms per time slot
                if len(options) >= max_options:
                    break
                    
                options.append({
                    'start_time': slot,
                    'end_time': end_time,
                    'room': room,
                    'room_name': f"{room.building_name} {room.room_number}",
                    'is_preferred': event.room_request and (
                        event.room_request in room.building_name or 
                        str(event.room_request) in str(room.room_number)
                    )
                })
        
        return options
    
    def schedule_event(self, event_id, start_time=None, room_id=None):
        """Schedule a single event with optional specific time and room"""
        event = Event.query.get(event_id)
        if not event:
            return None, "Event not found"
        
        if event.status != "submitted":
            return None, "Event must be submitted before scheduling"
        
        # Check if already scheduled
        existing_session = Session.query.filter_by(submission_id=event.id).first()
        if existing_session:
            return None, "Event is already scheduled"
        
        duration_minutes = event.session_length
        
        # If specific time and room provided, use those
        if start_time and room_id:
            start_datetime = datetime.combine(datetime.today(), start_time)
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            end_time = end_datetime.time()
            
            if self._check_room_availability(room_id, start_time, end_time):
                new_session = Session(
                    user_id=event.user_id,
                    submission_id=event.id,
                    room_id=room_id,
                    start_time=start_time,
                    end_time=end_time
                )
                db.session.add(new_session)
                db.session.commit()
                return new_session, "Event scheduled successfully"
            else:
                return None, "Selected time slot is not available"
        
        # Otherwise, try to find first available slot
        for slot in self.time_slots:
            start_datetime = datetime.combine(datetime.today(), slot)
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            end_time = end_datetime.time()
            
            # Check if end time is within working hours
            if end_time > time(17, 0):
                continue
            
            # Find suitable room
            rooms = self._find_suitable_rooms(event, slot, end_time)
            
            if rooms:
                room = rooms[0]  # Pick first suitable room
                new_session = Session(
                    user_id=event.user_id,
                    submission_id=event.id,
                    room_id=room.id,
                    start_time=slot,
                    end_time=end_time
                )
                db.session.add(new_session)
                db.session.commit()
                
                return new_session, "Event scheduled successfully"
        
        return None, "No available time slots or rooms found"
    
    def schedule_all_events(self):
        """Schedule all submitted but unscheduled events"""
        unscheduled_events = Event.query.filter(
            Event.status == "submitted",
            ~Event.id.in_(db.session.query(Session.submission_id))
        ).all()
        
        results = []
        for event in unscheduled_events:
            session, message = self.schedule_event(event.id)
            results.append({
                'event_id': event.id,
                'event_title': event.session_title,
                'success': session is not None,
                'message': message
            })
        
        return results
    
    def reschedule_event(self, session_id, new_start_time):
        """Reschedule an existing session to a new time"""
        session = Session.query.get(session_id)
        if not session:
            return None, "Session not found"
        
        event = Event.query.get(session.submission_id)
        duration_minutes = event.session_length
        
        start_datetime = datetime.combine(datetime.today(), new_start_time)
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        end_time = end_datetime.time()
        
        # Check if new time is available
        if self._check_room_availability(session.room_id, new_start_time, end_time, exclude_session_id=session.id):
            session.start_time = new_start_time
            session.end_time = end_time
            db.session.commit()
            return session, "Event rescheduled successfully"
        
        return None, "Time slot not available"