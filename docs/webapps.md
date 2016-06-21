Because there are so many things to pay attention to and so many clients that are different - desktop, mobile, browser, type of Internet connection etc. Here are some of the things which I consider important to build a nice scalable app. The lists below obviously depend on your non-functional requirements and may change, but here is a sample of what you might need to keep in mind:

#### Security
Security is important for everything we do on the web these days. From protecting the privacy of the users, to preventing malicious users to steal passwords or other user data. Here are the principles that we are going to follow:

* Use [HTTPS](https://letsencrypt.org/) from day one if you are sending passwords or any other sensitive content. The overhead is not worth it anymore and it's now practically free to do.
* [Encrypt passwords](https://www.owasp.org/index.php/Password_Storage_Cheat_Sheet) when storing them server side
* Use [CSRF](https://www.owasp.org/index.php/Cross-Site_Request_Forgery_(CSRF)) protection for anything that modifies data on your server.
* Never trust user input - [XSS](https://www.owasp.org/index.php/Cross-site_Scripting_(XSS))

For more on security, checkout [OWASP Top 10 (2013)](https://www.owasp.org/index.php/Top_10_2013-Top_10)

#### Speed
* Spawn tasks asynchronously whenever possible. Setup a scheduler for tasks in the future.
* Compress images as much as you can on sending responses
* Always use gzip for sending resources
* Set ETag and expiration date on static resources

#### Usability
* Web obesity crisis: Content &gt; Markup &gt; Images &gt; Style &gt; JS &gt; Fonts
* Set encoding utf-8 early on in head part
* Set meta mobile resizable tag in head
* Allow for internationalization
* Provide as much as you can from your application to not logged in users. Store a temporary user in a session cookie and notify him to sign up after some time saving all actions he has done so far
* Allow Facebook/Twitter/G+ sign-ins
* Set meta tags for open graph - allow sharing of the page
* Measure as much as you can especially early on
* Provide information to user if operation succeeded or not

#### Robustness
* Send emails on application crash, log the rest
* Unittest
* Set up continuous integration
* Use version control
* Create a Setup script or at the very least - README

#### SEO
* Use Javascript only for "extra" experience - the basic application should work with no javascript at all - forms, links etc can be overridden by simple js or at most - JQuery
* Setup different titles and descriptions on different pages. Titles should be about 80 characters, descriptions - about 160.
* Use proper h1/h2/h3... hierarchy and overall - use semantic HTML
#### Design rationale
* [motherfucking website](http://motherfuckingwebsite.com/)
* [better motherfucking website](http://bettermotherfuckingwebsite.com/)
* [webobesity crisis](http://idlewords.com/talks/website_obesity.htm)