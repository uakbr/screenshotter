import os
import time
from datetime import datetime
from PIL import Image
from AppKit import (
    NSPasteboard,
    NSPasteboardTypePNG,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSApplication,
    NSWorkspace,
    NSRunningApplication,
    NSAlert,
    NSAlertFirstButtonReturn,
    NSBundle,
)
import subprocess
from io import BytesIO
import sys
from PyObjCTools import AppHelper
import objc

# Import necessary frameworks for permissions
from Foundation import NSObject
from Quartz import CGWindowListCreateImage, kCGWindowListOptionOnScreenOnly, kCGNullWindowID, kCGWindowImageDefault

# For handling login items (startup)
from ServiceManagement import SMLoginItemSetEnabled

class ScreenshotApp(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        # Create the status bar item
        self.statusbar = NSStatusBar.systemStatusBar()
        self.statusitem = self.statusbar.statusItemWithLength_(-1)
        self.statusitem.button().setTitle_("\U0001F4F7")  # Camera emoji

        # Create the menu
        self.menu = NSMenu.alloc().init()

        # Capture Screenshot menu item
        self.capture_menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Capture", "captureScreenshot:", ""
        )
        self.capture_menuitem.setTarget_(self)
        self.menu.addItem_(self.capture_menuitem)

        # Run at Startup menu item
        self.startup_menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Run at Startup", "toggleStartup:", ""
        )
        self.startup_menuitem.setTarget_(self)
        self.startup_menuitem.setState_(self.is_login_item())
        self.menu.addItem_(self.startup_menuitem)

        # Quit menu item
        self.quit_menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "quitApp:", ""
        )
        self.quit_menuitem.setTarget_(self)
        self.menu.addItem_(self.quit_menuitem)

        self.statusitem.setMenu_(self.menu)

        # Check for Screen Recording permission
        self.check_screen_recording_permission()

    def is_login_item(self):
        # Check if the app is set to run at login
        login_items = self.get_login_items()
        app_path = NSBundle.mainBundle().bundlePath()
        return app_path in login_items

    def get_login_items(self):
        # Get the list of login items
        script = """
        tell application "System Events"
            get the path of every login item
        end tell
        """
        proc = subprocess.Popen(
            ['osascript', '-e', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = proc.communicate()
        login_items = out.decode().strip().split(", ")
        return login_items

    def toggleStartup_(self, sender):
        app_path = NSBundle.mainBundle().bundlePath()
        if sender.state() == 0:
            # Add to login items
            self.add_to_login_items(app_path)
            sender.setState_(1)
        else:
            # Remove from login items
            self.remove_from_login_items(app_path)
            sender.setState_(0)

    def add_to_login_items(self, app_path):
        script = f"""
        tell application "System Events"
            make login item at end with properties {{path: "{app_path}", hidden:false}}
        end tell
        """
        subprocess.call(['osascript', '-e', script])

    def remove_from_login_items(self, app_path):
        script = f"""
        tell application "System Events"
            delete login item "{os.path.basename(app_path)}"
        end tell
        """
        subprocess.call(['osascript', '-e', script])

    def check_screen_recording_permission(self):
        # Try to capture a small portion of the screen to check permission
        try:
            CGWindowListCreateImage(
                ((0, 0), (1, 1)),
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
                kCGWindowImageDefault,
            )
        except Exception:
            self.request_screen_recording_permission()

    def request_screen_recording_permission(self):
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Screen Recording Permission Required")
        alert.setInformativeText_(
            "To capture screenshots, please grant Screen Recording permission."
        )
        alert.addButtonWithTitle_("Open System Preferences")
        alert.addButtonWithTitle_("Quit")
        response = alert.runModal()
        if response == NSAlertFirstButtonReturn:
            subprocess.call(
                [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenRecording",
                ]
            )
        sys.exit()

    def captureScreenshot_(self, sender):
        # Define the folder on the desktop
        desktop = os.path.expanduser("~/Desktop")
        folder_name = "Screenshots"
        folder_path = os.path.join(desktop, folder_name)

        # Create the folder if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Use current date and time for the filename
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = os.path.join(folder_path, f"{current_time}.png")

        # Use macOS's screencapture tool for interactive capture
        subprocess.run(["screencapture", "-i", file_path])
        if os.path.exists(file_path):  # Ensure the screenshot was taken and saved
            screenshot = Image.open(file_path)
            self.copy_image_to_clipboard(screenshot)

    def copy_image_to_clipboard(self, img):
        pasteboard = NSPasteboard.generalPasteboard()
        pasteboard.declareTypes_owner_([NSPasteboardTypePNG], None)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        data = buffer.getvalue()
        pasteboard.setData_forType_(data, NSPasteboardTypePNG)

    def quitApp_(self, sender):
        NSApplication.sharedApplication().terminate_(self)

if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    delegate = ScreenshotApp.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()