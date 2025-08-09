"""Apple Script tools wrapper for minion-agent integration."""

import datetime
from typing import List, Optional

from smolagents import tool

from .apple_script import (
    Calendar, Contacts, Mail, Maps, Notes, 
    Reminders, SMS, SpotlightSearch, Zoom
)


# Initialize tool instances
calendar = Calendar()
contacts = Contacts()
mail = Mail()
maps = Maps()
notes = Notes()
reminders = Reminders()
sms = SMS()
spotlight_search = SpotlightSearch()



def create_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    location: str = "",
    notes: str = "",
    calendar_name: Optional[str] = None,
) -> str:
    """
    Creates a new calendar event.
    
    Args:
        title: Event title
        start_time: Start time in format "YYYY-MM-DD HH:MM:SS"
        end_time: End time in format "YYYY-MM-DD HH:MM:SS"
        location: Event location (optional)
        notes: Event notes (optional)
        calendar_name: Calendar name (optional, uses default if not provided)
    
    Returns:
        Success or error message
    """
    try:
        start_dt = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        
        return calendar.create_event(
            title=title,
            start_date=start_dt,
            end_date=end_dt,
            location=location,
            notes=notes,
            calendar=calendar_name
        )
    except ValueError as e:
        return f"Error parsing time format: {e}"



def create_reminder(
    name: str,
    due_date: Optional[str] = None,
    notes: str = "",
    list_name: str = "",
    priority: int = 0,
    all_day: bool = False,
) -> str:
    """
    Creates a new reminder.
    
    Args:
        name: Reminder name
        due_date: Due date in format "YYYY-MM-DD HH:MM:SS" (optional)
        notes: Reminder notes (optional)
        list_name: Reminder list name (optional)
        priority: Priority level 0-9 (optional)
        all_day: Whether it's an all-day reminder (optional)
    
    Returns:
        Success or error message
    """
    due_dt = None
    if due_date:
        try:
            due_dt = datetime.datetime.strptime(due_date, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            return f"Error parsing due date format: {e}"
    
    return reminders.create_reminder(
        name=name,
        due_date=due_dt,
        notes=notes,
        list_name=list_name,
        priority=priority,
        all_day=all_day
    )



def create_note(name: str, content: str, folder: Optional[str] = None) -> str:
    """
    Creates a new note.
    
    Args:
        name: Note name/title
        content: Note content
        folder: Folder name (optional, uses default if not provided)
    
    Returns:
        Success or error message
    """
    return notes.create_note(name=name, content=content, folder=folder)



def compose_email(
    recipients: List[str],
    subject: str,
    content: str,
    attachments: List[str] = None,
    cc: List[str] = None,
) -> str:
    """
    Composes a new email.
    
    Args:
        recipients: List of recipient email addresses
        subject: Email subject
        content: Email content
        attachments: List of file paths to attach (optional)
        cc: List of CC email addresses (optional)
    
    Returns:
        Success or error message
    """
    if attachments is None:
        attachments = []
    if cc is None:
        cc = []
        
    return mail.compose_email(
        recipients=recipients,
        subject=subject,
        content=content,
        attachments=attachments,
        cc=cc
    )



def send_sms(recipients: List[str], message: str) -> str:
    """
    Sends an SMS message.
    
    Args:
        recipients: List of phone numbers or contact names
        message: SMS message content
    
    Returns:
        Success or error message
    """
    return sms.send(to=recipients, message=message)



def get_contact_phone(contact_name: str) -> str:
    """
    Gets a contact's phone number by name.
    
    Args:
        contact_name: Contact name to search for
    
    Returns:
        Phone number or error message
    """
    return contacts.get_phone_number(contact_name)



def get_contact_email(contact_name: str) -> str:
    """
    Gets a contact's email address by name.
    
    Args:
        contact_name: Contact name to search for
    
    Returns:
        Email address or error message
    """
    return contacts.get_email_address(contact_name)



def open_location_maps(query: str) -> str:
    """
    Opens a location in Apple Maps.
    
    Args:
        query: Location query (place name, address, or coordinates)
    
    Returns:
        Success message with map URL
    """
    return maps.open_location(query)



def get_directions_maps(
    destination: str,
    start: str = "",
    transport: str = "driving"
) -> str:
    """
    Gets directions in Apple Maps.
    
    Args:
        destination: Destination location
        start: Starting location (optional, uses current location if empty)
        transport: Transportation mode - "driving", "walking", or "transit"
    
    Returns:
        Success message with directions URL
    """
    from .apple_script.maps import TransportationOptions
    
    transport_map = {
        "driving": TransportationOptions.DRIVING,
        "walking": TransportationOptions.WALKING,
        "transit": TransportationOptions.PUBLIC_TRANSIT,
        "public_transit": TransportationOptions.PUBLIC_TRANSIT,
    }
    
    transport_option = transport_map.get(transport.lower(), TransportationOptions.DRIVING)
    
    return maps.show_directions(
        end=destination,
        start=start,
        transport=transport_option
    )



def spotlight_search_open(query: str) -> str:
    """
    Opens an application or file using Spotlight search.
    
    Args:
        query: Application name, file name, or file path to open
    
    Returns:
        Success message with opened item path or error message
    """
    return spotlight_search.open(query)


# Export all tools
__all__ = [
    "create_calendar_event",
    "create_reminder", 
    "create_note",
    "compose_email",
    "send_sms",
    "get_contact_phone",
    "get_contact_email",
    "open_location_maps",
    "get_directions_maps",
    "spotlight_search_open"
] 