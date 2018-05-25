
from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import shutil
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

# Create your tests here.


TIMEOUT_SEC = 10

TEST_USER='malaria.test.user@gmail.com'
TEST_CRED='F@keUser1'

class RegisterStudy(LiveServerTestCase):

    # http://www.saltycrane.com/blog/2012/07/how-prevent-nose-unittest-using-docstring-when-verbosity-2/
    def shortDescription(self):
        return None
    
    def setUp(self):
        # setUp is where you instantiate the selenium webdriver and loads the browser.

        
        # Ensure that firefox doesn't look in the cache for jquery lib and css
        # http://stackoverflow.com/questions/16895606/firefox-selenium-webdriver-does-not-load-jquery-from-google-api
        profile = webdriver.FirefoxProfile()
        profile.set_preference("browser.cache.disk.enable", "false")
        profile.set_preference("browser.cache.memory.enable", "false")
        profile.set_preference("browser.cache.offline.enable", "false")
        profile.set_preference("network.http.use-cache", "false")

        binary = FirefoxBinary(shutil.which("firefox"))
        self.selenium = webdriver.Firefox(firefox_profile=profile, firefox_binary=binary)
        
        self.selenium.maximize_window()
        self.selenium.implicitly_wait(TIMEOUT_SEC)  # Wait up to TIMEOUT_SEC seconds until we timeout when finding elements.  By default, django polls every 0.5s

        super().setUp()


    def tearDown(self):
        # Call tearDown to close the web browser
#        self.selenium.quit()
#        super().tearDown()
        pass

    def test_login(self):
        """
        BACKGROUND:  User with coordinator role exists in ROMA
            Given:    User with coordinator role exists in ROMA
                    | username                           | email                        | password        | first_name        | last_name        | study_manager    |
                    | malaria.test.user@gmail.com        |malaria.test.user@gmail.com   | F@keUser1       | Malaria           | TestUser         | 1                |
                    
            
        SCENARIO: Create study with 2 locations and 2 members
        GIVEN:  I logon as malaria.test.user@gmail.com with coordinator role
        WHEN:    I create a study with 2 locations, and add 2 study members
        AND:  1 of the locations uses the other as a proxy
        THEN:    The study is created successfully and associated with the locations and study members
        """
        # Test logging onto the login site directly
        self.selenium.get(self.live_server_url + '/polls')
        username_txtbox = self.selenium.find_element_by_id("username")
        username_txtbox.send_keys(TEST_USER)
        password_txtbox = self.selenium.find_element_by_id("password")
        password_txtbox.send_keys(TEST_CRED)
        logon_submit_button = self.selenium.find_element_by_name("submit")
        logon_submit_button.click()
         
        
        hello = self.selenium.find_element_by_id('hello')
        self.assertEquals(hello.text, "Hello, world. You are at the polls index.")

        user = self.selenium.find_element_by_id('user')
        self.assertEquals(user.text, TEST_USER)
