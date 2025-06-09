from dotenv import load_dotenv
load_dotenv()

from app import create_app
from email_service import email_service

app = create_app()

with app.app_context():
    class TestUser:
        def __init__(self):
            self.name = "Test Parent"
            self.email = "baidoldamarat@gmail.com" 
    
    test_user = TestUser()
    
    print("🧪 Testing welcome email...")
    print(f"📧 Sending to: {test_user.email}")
    print(f"🌐 Base URL: {app.config.get('BASE_URL')}")
    
    try:
        result = email_service.send_welcome_email(test_user, 'parent')
        print("✅ Welcome email sent successfully!")
        print("📬 Check your inbox for the welcome email")
        print("🕐 Email is being sent in background, may take a few seconds")
        
        if result:
            result.join(timeout=10)  
            print("✅ Email thread completed")
        
    except Exception as e:
        print(f"❌ Welcome email failed: {e}")
        
        import os
        template_files = [
            'templates/emails/base.html',
            'templates/emails/welcome.html',
            'templates/emails/welcome.txt'
        ]
        
        print("\n🔍 Checking email templates:")
        for template in template_files:
            if os.path.exists(template):
                print(f"✅ {template} - Found")
            else:
                print(f"❌ {template} - Missing")
        
        if not all(os.path.exists(t) for t in template_files):
            print("\n💡 You need to create the missing email templates!")
            print("📁 Create the templates/emails/ directory and add the template files")