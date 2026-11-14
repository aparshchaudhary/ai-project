"""
Custom ML Intent Dataset Generator.
Generates an extensive, multilingual (English, Hindi, Hinglish) dataset
covering the 12 target intents with entity metadata and balanced splits.
"""

from __future__ import annotations
import json
import random
from pathlib import Path
from typing import List, Dict, Any

from backend.config.settings import settings

INTENT_CLASSES = [
    "CALL_CONTACT",
    "SEND_WHATSAPP_MESSAGE",
    "OPEN_APPLICATION",
    "SEARCH_WEB",
    "SEARCH_FILE",
    "CREATE_FOLDER",
    "NAVIGATE_FOLDER",
    "OPEN_SETTINGS",
    "CONTROL_MEDIA",
    "CREATE_REMINDER",
    "CHECK_SYSTEM_STATUS",
    "CROSS_DEVICE_TRANSFER"
]

RAW_SAMPLES: List[Dict[str, Any]] = [
    # 1. CALL_CONTACT
    {"text": "Call Dad", "intent": "CALL_CONTACT", "language": "en", "entities": {"contact": "Dad"}},
    {"text": "Call Mom immediately", "intent": "CALL_CONTACT", "language": "en", "entities": {"contact": "Mom"}},
    {"text": "Make a phone call to Rahul", "intent": "CALL_CONTACT", "language": "en", "entities": {"contact": "Rahul"}},
    {"text": "Dial Priya's number", "intent": "CALL_CONTACT", "language": "en", "entities": {"contact": "Priya"}},
    {"text": "Please call Ram Sharma right now", "intent": "CALL_CONTACT", "language": "en", "entities": {"contact": "Ram Sharma"}},
    {"text": "Find Rahul in my contacts and call him", "intent": "CALL_CONTACT", "language": "en", "entities": {"contact": "Rahul"}},
    {"text": "Phone call lagao Dad ko", "intent": "CALL_CONTACT", "language": "hinglish", "entities": {"contact": "Dad"}},
    {"text": "Mom ko phone karo", "intent": "CALL_CONTACT", "language": "hinglish", "entities": {"contact": "Mom"}},
    {"text": "Rahul ko call lagao", "intent": "CALL_CONTACT", "language": "hinglish", "entities": {"contact": "Rahul"}},
    {"text": "Ram ko turant call karo", "intent": "CALL_CONTACT", "language": "hinglish", "entities": {"contact": "Ram"}},
    {"text": "Papa ko call milao", "intent": "CALL_CONTACT", "language": "hi", "entities": {"contact": "Papa"}},
    {"text": "Maa ko phone lagao", "intent": "CALL_CONTACT", "language": "hi", "entities": {"contact": "Maa"}},
    {"text": "Bhai ko phone karo jaldi", "intent": "CALL_CONTACT", "language": "hi", "entities": {"contact": "Bhai"}},
    {"text": "Can you place a call to Amit", "intent": "CALL_CONTACT", "language": "en", "entities": {"contact": "Amit"}},
    {"text": "Start a voice call with John", "intent": "CALL_CONTACT", "language": "en", "entities": {"contact": "John"}},
    {"text": "Call my brother on phone", "intent": "CALL_CONTACT", "language": "en", "entities": {"contact": "brother"}},
    {"text": "Didi ko call lagao phone par", "intent": "CALL_CONTACT", "language": "hinglish", "entities": {"contact": "Didi"}},
    {"text": "Call lagao Rohit ko", "intent": "CALL_CONTACT", "language": "hinglish", "entities": {"contact": "Rohit"}},

    # 2. SEND_WHATSAPP_MESSAGE
    {"text": "Open WhatsApp and send Hi to Dad", "intent": "SEND_WHATSAPP_MESSAGE", "language": "en", "entities": {"contact": "Dad", "message": "Hi"}},
    {"text": "Tell Rahul that I will reach in 10 minutes", "intent": "SEND_WHATSAPP_MESSAGE", "language": "en", "entities": {"contact": "Rahul", "message": "I will reach in 10 minutes"}},
    {"text": "Message Ram saying the meeting is at 5 PM", "intent": "SEND_WHATSAPP_MESSAGE", "language": "en", "entities": {"contact": "Ram", "message": "the meeting is at 5 PM"}},
    {"text": "Send a WhatsApp message to Mom: I am heading home", "intent": "SEND_WHATSAPP_MESSAGE", "language": "en", "entities": {"contact": "Mom", "message": "I am heading home"}},
    {"text": "Text Priya that I sent the project files", "intent": "SEND_WHATSAPP_MESSAGE", "language": "en", "entities": {"contact": "Priya", "message": "I sent the project files"}},
    {"text": "WhatsApp Rahul Hello", "intent": "SEND_WHATSAPP_MESSAGE", "language": "en", "entities": {"contact": "Rahul", "message": "Hello"}},
    {"text": "Dad ko WhatsApp par message bhejo: Good morning", "intent": "SEND_WHATSAPP_MESSAGE", "language": "hinglish", "entities": {"contact": "Dad", "message": "Good morning"}},
    {"text": "Ram ko bolo ki main thodi der mein aata hoon", "intent": "SEND_WHATSAPP_MESSAGE", "language": "hinglish", "entities": {"contact": "Ram", "message": "main thodi der mein aata hoon"}},
    {"text": "Rahul ko message bhejo I am coming", "intent": "SEND_WHATSAPP_MESSAGE", "language": "hinglish", "entities": {"contact": "Rahul", "message": "I am coming"}},
    {"text": "Mom ko bolo dinner ready rakhna", "intent": "SEND_WHATSAPP_MESSAGE", "language": "hinglish", "entities": {"contact": "Mom", "message": "dinner ready rakhna"}},
    {"text": "Priya ko WhatsApp karo ki meeting cancel ho gayi", "intent": "SEND_WHATSAPP_MESSAGE", "language": "hinglish", "entities": {"contact": "Priya", "message": "meeting cancel ho gayi"}},
    {"text": "Papa ko sandesh bhejo main pahunch gaya hoon", "intent": "SEND_WHATSAPP_MESSAGE", "language": "hi", "entities": {"contact": "Papa", "message": "main pahunch gaya hoon"}},
    {"text": "Maa ko WhatsApp sandesh bhejo", "intent": "SEND_WHATSAPP_MESSAGE", "language": "hi", "entities": {"contact": "Maa"}},
    {"text": "Send Hi to Amit on WhatsApp", "intent": "SEND_WHATSAPP_MESSAGE", "language": "en", "entities": {"contact": "Amit", "message": "Hi"}},
    {"text": "Drop a message to boss saying I am sick today", "intent": "SEND_WHATSAPP_MESSAGE", "language": "en", "entities": {"contact": "boss", "message": "I am sick today"}},
    {"text": "Tell Sarah that project is completed", "intent": "SEND_WHATSAPP_MESSAGE", "language": "en", "entities": {"contact": "Sarah", "message": "project is completed"}},
    {"text": "WhatsApp pe message karo Amit ko Hello", "intent": "SEND_WHATSAPP_MESSAGE", "language": "hinglish", "entities": {"contact": "Amit", "message": "Hello"}},
    {"text": "Send text to brother saying call me back", "intent": "SEND_WHATSAPP_MESSAGE", "language": "en", "entities": {"contact": "brother", "message": "call me back"}},

    # 3. OPEN_APPLICATION
    {"text": "Open Google Chrome", "intent": "OPEN_APPLICATION", "language": "en", "entities": {"application": "chrome"}},
    {"text": "Open Chrome browser", "intent": "OPEN_APPLICATION", "language": "en", "entities": {"application": "chrome"}},
    {"text": "Launch VS Code", "intent": "OPEN_APPLICATION", "language": "en", "entities": {"application": "code"}},
    {"text": "Open Notepad", "intent": "OPEN_APPLICATION", "language": "en", "entities": {"application": "notepad"}},
    {"text": "Start Calculator", "intent": "OPEN_APPLICATION", "language": "en", "entities": {"application": "calculator"}},
    {"text": "Launch Spotify", "intent": "OPEN_APPLICATION", "language": "en", "entities": {"application": "spotify"}},
    {"text": "Open File Explorer", "intent": "OPEN_APPLICATION", "language": "en", "entities": {"application": "explorer"}},
    {"text": "Open Microsoft Edge", "intent": "OPEN_APPLICATION", "language": "en", "entities": {"application": "msedge"}},
    {"text": "Chrome kholo", "intent": "OPEN_APPLICATION", "language": "hinglish", "entities": {"application": "chrome"}},
    {"text": "Notepad chalu karo", "intent": "OPEN_APPLICATION", "language": "hinglish", "entities": {"application": "notepad"}},
    {"text": "Calculator open karo", "intent": "OPEN_APPLICATION", "language": "hinglish", "entities": {"application": "calculator"}},
    {"text": "VS Code start karo", "intent": "OPEN_APPLICATION", "language": "hinglish", "entities": {"application": "code"}},
    {"text": "Spotify chalao", "intent": "OPEN_APPLICATION", "language": "hinglish", "entities": {"application": "spotify"}},
    {"text": "Browser kholo jaldi", "intent": "OPEN_APPLICATION", "language": "hinglish", "entities": {"application": "chrome"}},
    {"text": "Kholo Calculator app", "intent": "OPEN_APPLICATION", "language": "hinglish", "entities": {"application": "calculator"}},
    {"text": "Google Chrome kholein", "intent": "OPEN_APPLICATION", "language": "hi", "entities": {"application": "chrome"}},
    {"text": "Notepad kholo aur likho", "intent": "OPEN_APPLICATION", "language": "hi", "entities": {"application": "notepad"}},
    {"text": "Launch the music player", "intent": "OPEN_APPLICATION", "language": "en", "entities": {"application": "spotify"}},

    # 4. SEARCH_WEB
    {"text": "Search Google for Artificial Intelligence", "intent": "SEARCH_WEB", "language": "en", "entities": {"query": "Artificial Intelligence"}},
    {"text": "Open Chrome and search about machine learning", "intent": "SEARCH_WEB", "language": "en", "entities": {"query": "machine learning"}},
    {"text": "Google python programming tutorials", "intent": "SEARCH_WEB", "language": "en", "entities": {"query": "python programming tutorials"}},
    {"text": "Search on web what is quantum computing", "intent": "SEARCH_WEB", "language": "en", "entities": {"query": "what is quantum computing"}},
    {"text": "Look up today's weather in Mumbai", "intent": "SEARCH_WEB", "language": "en", "entities": {"query": "today's weather in Mumbai"}},
    {"text": "Search YouTube for AI agent architecture", "intent": "SEARCH_WEB", "language": "en", "entities": {"query": "AI agent architecture"}},
    {"text": "Google par search karo Artificial Intelligence", "intent": "SEARCH_WEB", "language": "hinglish", "entities": {"query": "Artificial Intelligence"}},
    {"text": "Chrome mein dhoondo deep learning course", "intent": "SEARCH_WEB", "language": "hinglish", "entities": {"query": "deep learning course"}},
    {"text": "Internet par search karo latest news", "intent": "SEARCH_WEB", "language": "hinglish", "entities": {"query": "latest news"}},
    {"text": "Dhoondho python tutorials online", "intent": "SEARCH_WEB", "language": "hinglish", "entities": {"query": "python tutorials online"}},
    {"text": "Web par search karo generative ai", "intent": "SEARCH_WEB", "language": "hinglish", "entities": {"query": "generative ai"}},
    {"text": "Internet par khojo bharat ka itihas", "intent": "SEARCH_WEB", "language": "hi", "entities": {"query": "bharat ka itihas"}},
    {"text": "Google par khojiye aaj ka taapmaan", "intent": "SEARCH_WEB", "language": "hi", "entities": {"query": "aaj ka taapmaan"}},
    {"text": "Find information about autonomous agents online", "intent": "SEARCH_WEB", "language": "en", "entities": {"query": "autonomous agents"}},
    {"text": "Search the web for stock market updates", "intent": "SEARCH_WEB", "language": "en", "entities": {"query": "stock market updates"}},
    {"text": "Chrome kholo aur AI search karo", "intent": "SEARCH_WEB", "language": "hinglish", "entities": {"query": "AI"}},

    # 5. SEARCH_FILE
    {"text": "Find my resume", "intent": "SEARCH_FILE", "language": "en", "entities": {"filename": "resume"}},
    {"text": "Search for invoice PDF in Documents", "intent": "SEARCH_FILE", "language": "en", "entities": {"filename": "invoice.pdf"}},
    {"text": "Find the project report document", "intent": "SEARCH_FILE", "language": "en", "entities": {"filename": "project report"}},
    {"text": "Where is my resume file", "intent": "SEARCH_FILE", "language": "en", "entities": {"filename": "resume"}},
    {"text": "Locate annual budget spreadsheet", "intent": "SEARCH_FILE", "language": "en", "entities": {"filename": "annual budget"}},
    {"text": "Search for file called presentation ppt", "intent": "SEARCH_FILE", "language": "en", "entities": {"filename": "presentation.ppt"}},
    {"text": "Mera resume dhoondo", "intent": "SEARCH_FILE", "language": "hinglish", "entities": {"filename": "resume"}},
    {"text": "Documents mein invoice file search karo", "intent": "SEARCH_FILE", "language": "hinglish", "entities": {"filename": "invoice"}},
    {"text": "Laptop par report file kahan hai", "intent": "SEARCH_FILE", "language": "hinglish", "entities": {"filename": "report"}},
    {"text": "Dhoondo resume.pdf ko", "intent": "SEARCH_FILE", "language": "hinglish", "entities": {"filename": "resume.pdf"}},
    {"text": "Meri resume file khojo", "intent": "SEARCH_FILE", "language": "hi", "entities": {"filename": "resume"}},
    {"text": "Documents mein report file dhoondhein", "intent": "SEARCH_FILE", "language": "hi", "entities": {"filename": "report"}},
    {"text": "Find my tax returns file on PC", "intent": "SEARCH_FILE", "language": "en", "entities": {"filename": "tax returns"}},
    {"text": "Search for Python script file in Downloads", "intent": "SEARCH_FILE", "language": "en", "entities": {"filename": "script.py"}},
    {"text": "Locate my passport scan PDF", "intent": "SEARCH_FILE", "language": "en", "entities": {"filename": "passport scan"}},

    # 6. CREATE_FOLDER
    {"text": "Create a folder called AI Projects", "intent": "CREATE_FOLDER", "language": "en", "entities": {"folder_name": "AI Projects"}},
    {"text": "Make a new directory named Client Invoices", "intent": "CREATE_FOLDER", "language": "en", "entities": {"folder_name": "Client Invoices"}},
    {"text": "Create folder Machine Learning in Documents", "intent": "CREATE_FOLDER", "language": "en", "entities": {"folder_name": "Machine Learning"}},
    {"text": "New folder banao Python Projects naam se", "intent": "CREATE_FOLDER", "language": "hinglish", "entities": {"folder_name": "Python Projects"}},
    {"text": "AI Projects naam ka folder banao", "intent": "CREATE_FOLDER", "language": "hinglish", "entities": {"folder_name": "AI Projects"}},
    {"text": "Desktop par Backup folder create karo", "intent": "CREATE_FOLDER", "language": "hinglish", "entities": {"folder_name": "Backup"}},
    {"text": "Ek naya folder banao Study Material", "intent": "CREATE_FOLDER", "language": "hi", "entities": {"folder_name": "Study Material"}},
    {"text": "Documents mein Accounts naam ka folder banayein", "intent": "CREATE_FOLDER", "language": "hi", "entities": {"folder_name": "Accounts"}},
    {"text": "Create directory Test Suite in safe folder", "intent": "CREATE_FOLDER", "language": "en", "entities": {"folder_name": "Test Suite"}},
    {"text": "Make a new folder called Personal Photos", "intent": "CREATE_FOLDER", "language": "en", "entities": {"folder_name": "Personal Photos"}},
    {"text": "Naya folder create karo Meeting Notes", "intent": "CREATE_FOLDER", "language": "hinglish", "entities": {"folder_name": "Meeting Notes"}},

    # 7. NAVIGATE_FOLDER
    {"text": "Open my Downloads folder", "intent": "NAVIGATE_FOLDER", "language": "en", "entities": {"folder": "downloads"}},
    {"text": "Navigate to Documents", "intent": "NAVIGATE_FOLDER", "language": "en", "entities": {"folder": "documents"}},
    {"text": "Show my Desktop directory", "intent": "NAVIGATE_FOLDER", "language": "en", "entities": {"folder": "desktop"}},
    {"text": "Open Videos folder", "intent": "NAVIGATE_FOLDER", "language": "en", "entities": {"folder": "videos"}},
    {"text": "Go to Music folder", "intent": "NAVIGATE_FOLDER", "language": "en", "entities": {"folder": "music"}},
    {"text": "Downloads folder kholo", "intent": "NAVIGATE_FOLDER", "language": "hinglish", "entities": {"folder": "downloads"}},
    {"text": "Documents directory mein jao", "intent": "NAVIGATE_FOLDER", "language": "hinglish", "entities": {"folder": "documents"}},
    {"text": "Desktop khol kar dikhao", "intent": "NAVIGATE_FOLDER", "language": "hinglish", "entities": {"folder": "desktop"}},
    {"text": "Mera Downloads kholo", "intent": "NAVIGATE_FOLDER", "language": "hinglish", "entities": {"folder": "downloads"}},
    {"text": "Downloads folder kholein", "intent": "NAVIGATE_FOLDER", "language": "hi", "entities": {"folder": "downloads"}},
    {"text": "Desktop directory kholein", "intent": "NAVIGATE_FOLDER", "language": "hi", "entities": {"folder": "desktop"}},
    {"text": "Open the Downloads directory in Explorer", "intent": "NAVIGATE_FOLDER", "language": "en", "entities": {"folder": "downloads"}},
    {"text": "Open my safe documents folder", "intent": "NAVIGATE_FOLDER", "language": "en", "entities": {"folder": "documents"}},

    # 8. OPEN_SETTINGS
    {"text": "Open my phone settings", "intent": "OPEN_SETTINGS", "language": "en", "entities": {"target_device": "android"}},
    {"text": "Open Windows settings", "intent": "OPEN_SETTINGS", "language": "en", "entities": {"target_device": "windows"}},
    {"text": "Turn on Bluetooth", "intent": "OPEN_SETTINGS", "language": "en", "entities": {"setting": "bluetooth", "action": "on"}},
    {"text": "Turn off Bluetooth", "intent": "OPEN_SETTINGS", "language": "en", "entities": {"setting": "bluetooth", "action": "off"}},
    {"text": "Toggle WiFi state", "intent": "OPEN_SETTINGS", "language": "en", "entities": {"setting": "wifi"}},
    {"text": "Phone ki settings kholo", "intent": "OPEN_SETTINGS", "language": "hinglish", "entities": {"target_device": "android"}},
    {"text": "Bluetooth on karo phone par", "intent": "OPEN_SETTINGS", "language": "hinglish", "entities": {"setting": "bluetooth", "action": "on"}},
    {"text": "Bluetooth band kar do", "intent": "OPEN_SETTINGS", "language": "hinglish", "entities": {"setting": "bluetooth", "action": "off"}},
    {"text": "System settings open karo", "intent": "OPEN_SETTINGS", "language": "hinglish", "entities": {"target_device": "windows"}},
    {"text": "Phone ki setting kholein", "intent": "OPEN_SETTINGS", "language": "hi", "entities": {"target_device": "android"}},
    {"text": "Bluetooth chalu karein", "intent": "OPEN_SETTINGS", "language": "hi", "entities": {"setting": "bluetooth", "action": "on"}},
    {"text": "Enable Bluetooth on mobile", "intent": "OPEN_SETTINGS", "language": "en", "entities": {"setting": "bluetooth", "action": "on"}},
    {"text": "Launch device settings panel", "intent": "OPEN_SETTINGS", "language": "en"},

    # 9. CONTROL_MEDIA
    {"text": "Open Spotify and play my playlist", "intent": "CONTROL_MEDIA", "language": "en", "entities": {"application": "spotify"}},
    {"text": "Play next song", "intent": "CONTROL_MEDIA", "language": "en", "entities": {"action": "next"}},
    {"text": "Pause the music playback", "intent": "CONTROL_MEDIA", "language": "en", "entities": {"action": "pause"}},
    {"text": "Turn volume up", "intent": "CONTROL_MEDIA", "language": "en", "entities": {"action": "volume_up"}},
    {"text": "Mute audio output", "intent": "CONTROL_MEDIA", "language": "en", "entities": {"action": "mute"}},
    {"text": "Gaana bajao Spotify par", "intent": "CONTROL_MEDIA", "language": "hinglish", "entities": {"application": "spotify"}},
    {"text": "Agla gaana chalao", "intent": "CONTROL_MEDIA", "language": "hinglish", "entities": {"action": "next"}},
    {"text": "Awaaz badhao thodi", "intent": "CONTROL_MEDIA", "language": "hinglish", "entities": {"action": "volume_up"}},
    {"text": "Awaaz kam karo", "intent": "CONTROL_MEDIA", "language": "hinglish", "entities": {"action": "volume_down"}},
    {"text": "Music band karo", "intent": "CONTROL_MEDIA", "language": "hinglish", "entities": {"action": "pause"}},
    {"text": "Sangeet roko", "intent": "CONTROL_MEDIA", "language": "hi", "entities": {"action": "pause"}},
    {"text": "Awaaz tezz karein", "intent": "CONTROL_MEDIA", "language": "hi", "entities": {"action": "volume_up"}},
    {"text": "Resume track on Spotify", "intent": "CONTROL_MEDIA", "language": "en", "entities": {"action": "play"}},
    {"text": "Skip this song", "intent": "CONTROL_MEDIA", "language": "en", "entities": {"action": "next"}},

    # 10. CREATE_REMINDER
    {"text": "Set an alarm for 7 AM", "intent": "CREATE_REMINDER", "language": "en", "entities": {"time": "7 AM", "type": "alarm"}},
    {"text": "Remind me to call Mom at 6 PM", "intent": "CREATE_REMINDER", "language": "en", "entities": {"time": "6 PM", "task": "call Mom"}},
    {"text": "Set a reminder for team standup tomorrow morning", "intent": "CREATE_REMINDER", "language": "en", "entities": {"time": "tomorrow morning", "task": "team standup"}},
    {"text": "Create a timer for 25 minutes", "intent": "CREATE_REMINDER", "language": "en", "entities": {"duration": "25 minutes", "type": "timer"}},
    {"text": "7 baje ka alarm lagao", "intent": "CREATE_REMINDER", "language": "hinglish", "entities": {"time": "7:00", "type": "alarm"}},
    {"text": "Mujhe shaam 5 baje yaad dilana meeting hai", "intent": "CREATE_REMINDER", "language": "hinglish", "entities": {"time": "5 PM", "task": "meeting"}},
    {"text": "Kal subah 8 baje ka reminder set karo", "intent": "CREATE_REMINDER", "language": "hinglish", "entities": {"time": "8 AM", "task": "reminder"}},
    {"text": "Alarm lagao subah 6 baje", "intent": "CREATE_REMINDER", "language": "hi", "entities": {"time": "6:00", "type": "alarm"}},
    {"text": "Mujhe kal davaai lene ki yaad dilayein", "intent": "CREATE_REMINDER", "language": "hi", "entities": {"task": "davaai"}},
    {"text": "Set wake up alarm for 6:30 AM", "intent": "CREATE_REMINDER", "language": "en", "entities": {"time": "6:30 AM", "type": "alarm"}},
    {"text": "Remind me to drink water every 2 hours", "intent": "CREATE_REMINDER", "language": "en", "entities": {"task": "drink water"}},

    # 11. CHECK_SYSTEM_STATUS
    {"text": "Check my laptop's RAM and storage", "intent": "CHECK_SYSTEM_STATUS", "language": "en", "entities": {"target_device": "windows"}},
    {"text": "Check my laptop's battery status", "intent": "CHECK_SYSTEM_STATUS", "language": "en", "entities": {"target_device": "windows"}},
    {"text": "What is my current CPU and memory usage", "intent": "CHECK_SYSTEM_STATUS", "language": "en"},
    {"text": "How much battery is left on my computer", "intent": "CHECK_SYSTEM_STATUS", "language": "en"},
    {"text": "Check phone battery and storage", "intent": "CHECK_SYSTEM_STATUS", "language": "en", "entities": {"target_device": "android"}},
    {"text": "Laptop ki battery aur RAM check karo", "intent": "CHECK_SYSTEM_STATUS", "language": "hinglish", "entities": {"target_device": "windows"}},
    {"text": "Computer ka hardware status batao", "intent": "CHECK_SYSTEM_STATUS", "language": "hinglish"},
    {"text": "RAM kitni free hai check karo", "intent": "CHECK_SYSTEM_STATUS", "language": "hinglish"},
    {"text": "Battery kitni bachi hai laptop mein", "intent": "CHECK_SYSTEM_STATUS", "language": "hinglish", "entities": {"target_device": "windows"}},
    {"text": "Computer ki battery sthiti dekhein", "intent": "CHECK_SYSTEM_STATUS", "language": "hi"},
    {"text": "Storage kitna khali hai laptop par", "intent": "CHECK_SYSTEM_STATUS", "language": "hi"},
    {"text": "Display system performance metrics", "intent": "CHECK_SYSTEM_STATUS", "language": "en"},
    {"text": "Tell me laptop specifications and battery", "intent": "CHECK_SYSTEM_STATUS", "language": "en"},

    # 12. CROSS_DEVICE_TRANSFER
    {"text": "Find my resume on my laptop and send it to Dad on WhatsApp", "intent": "CROSS_DEVICE_TRANSFER", "language": "en", "entities": {"filename": "resume", "source": "windows", "target": "android", "contact": "Dad"}},
    {"text": "Show my laptop's battery status on my phone", "intent": "CROSS_DEVICE_TRANSFER", "language": "en", "entities": {"source": "windows", "target": "android", "metric": "battery"}},
    {"text": "Find the PDF on my phone and open it on my laptop", "intent": "CROSS_DEVICE_TRANSFER", "language": "en", "entities": {"filename": "PDF", "source": "android", "target": "windows"}},
    {"text": "Transfer this file from my laptop to my phone", "intent": "CROSS_DEVICE_TRANSFER", "language": "en", "entities": {"source": "windows", "target": "android"}},
    {"text": "Send this document from PC to mobile phone", "intent": "CROSS_DEVICE_TRANSFER", "language": "en", "entities": {"source": "windows", "target": "android"}},
    {"text": "Laptop se resume phone par bhejo", "intent": "CROSS_DEVICE_TRANSFER", "language": "hinglish", "entities": {"filename": "resume", "source": "windows", "target": "android"}},
    {"text": "Phone ka PDF laptop par kholo", "intent": "CROSS_DEVICE_TRANSFER", "language": "hinglish", "entities": {"filename": "PDF", "source": "android", "target": "windows"}},
    {"text": "Laptop ki battery phone par dikhao", "intent": "CROSS_DEVICE_TRANSFER", "language": "hinglish", "entities": {"source": "windows", "target": "android"}},
    {"text": "Ye file computer se mobile par transfer karo", "intent": "CROSS_DEVICE_TRANSFER", "language": "hinglish", "entities": {"source": "windows", "target": "android"}},
    {"text": "Laptop se file phone mein bheinjiye", "intent": "CROSS_DEVICE_TRANSFER", "language": "hi", "entities": {"source": "windows", "target": "android"}},
    {"text": "Mobile se tasveer laptop par transfer karein", "intent": "CROSS_DEVICE_TRANSFER", "language": "hi", "entities": {"source": "android", "target": "windows"}},
    {"text": "Transfer report from phone to my computer", "intent": "CROSS_DEVICE_TRANSFER", "language": "en", "entities": {"source": "android", "target": "windows"}},
    {"text": "Share file between laptop and phone", "intent": "CROSS_DEVICE_TRANSFER", "language": "en"}
]


def augment_samples(samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Applies clean linguistic data augmentation (prefix variations, polite forms,
    case variations, and noise injection) to produce a robust 350+ item dataset.
    """
    augmented = list(samples)
    prefixes_en = ["Please", "Can you", "Could you please", "Quickly", "Hey assistant", "Kindly"]
    prefixes_hi = ["Zara", "Kripya", "Jaldi se", "Bhai", "Sunno"]

    for item in samples:
        text = item["text"]
        lang = item["language"]
        intent = item["intent"]
        entities = item.get("entities", {})

        if lang == "en":
            for p in prefixes_en[:2]:
                augmented.append({
                    "text": f"{p} {text[0].lower() + text[1:]}",
                    "intent": intent,
                    "language": "en",
                    "entities": entities
                })
        elif lang in ["hinglish", "hi"]:
            for p in prefixes_hi[:2]:
                augmented.append({
                    "text": f"{p} {text[0].lower() + text[1:]}",
                    "intent": intent,
                    "language": lang,
                    "entities": entities
                })

        # Add punctuation variation
        augmented.append({
            "text": f"{text}.",
            "intent": intent,
            "language": lang,
            "entities": entities
        })

    # Deduplicate by normalized text
    seen = set()
    deduped = []
    for s in augmented:
        norm = s["text"].strip().lower()
        if norm not in seen:
            seen.add(norm)
            deduped.append(s)

    random.seed(42)
    random.shuffle(deduped)
    return deduped


def generate_and_save_dataset() -> Path:
    """Generates the full dataset and writes to data/ml/intent_dataset.json."""
    output_dir = settings.data_dir / "ml"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "intent_dataset.json"

    dataset = augment_samples(RAW_SAMPLES)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "version": "1.0.0",
            "intents": INTENT_CLASSES,
            "total_samples": len(dataset),
            "samples": dataset
        }, f, indent=2, ensure_ascii=False)

    return out_file


if __name__ == "__main__":
    p = generate_and_save_dataset()
    print(f"Generated intent dataset with metadata at {p}")
