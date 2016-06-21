# The organization
## What is the organizational chart? Who is responsible for what?

President
Reports to shareholders
Responsibilities:
Ensures company is providing value
Secure capital
Hiring people and making sure they fit into company’s values

Assigned: Tomasz Sadowski
VP Sales & Marketing
Reports to President.
Responsibilities:
Finding customers and opportunities
Going to meetings
Finding leads, tools to do marketing better

Assigned: Tomasz Sadowski
Sales Manager
Reports to VP Marketing
Responsibilities:
Designing the sales process
Contacting leads and taking them through the sales process
cold calling

Assigned: Daniel Tsvetkov
Marketing Manager
Reports to VP Marketing
Responsibilities:
Communicating company’s identity, values and mission through branding
Making website graphics
Writing Articles about reviews
Design email marketing strategy and work on writing emails

Assigned: Daniel Tsvetkov
VP Finance
Reports to President
Responsibilities:
Forecasting
Monitoring and managing money in and money out

Assigned: Daniel Tsvetkov
VP Product
Reports to President
Responsibilities:
Defining requirements
Planning for product improvements

Assigned: Tomasz Sadowski
Customer Support Manager
Reports to VP Product
Responsibilities:
Resolving customer’s issues
Backlogging customer’s requests

Assigned: Tomasz Sadowski
Technology Manager
Reports to VP Product
Responsibilities:
Choosing the underlying technology
Implementing and testing the product

Assigned: Daniel Tsvetkov
Research and Development
Reports to Technology Manager
Responsibilities:
Researching new technologies and methods to push the boundaries of the product’s awesomeness

Assigned: Tomasz Sadowski


### How many people in a team? What are their roles?

### How many hours am I expected to work?
Working more than 40-hour weeks regularly decreases productivity. [We don't do it](https://www.salon.com/2012/03/14/bring_back_the_40_hour_work_week/). We strive for work completion and value sanity, work-life balance over long hours.

### How do you measure productivity?
We use a system developed by Google called [OKR](https://en.wikipedia.org/wiki/OKR) (Objectives and Key Results). Basically it means that you set your goals and how you would measure them, then you execute and measure them comparing expected to actual. It should be around 0.8 (too low = unacomplished; too high - you have set a low goal; we prefer lower grades than seeing >=1s).

### What is the work schedule in a typical day? Week?
Nothing is strictly enforced but there are some recommendations.
* Decide what are the things that you want to work on the day before. Have a good night sleep.
* Pick the easest task in the morning.
* Take regular breaks - water, coffee, just hang out for 10 minutes. Your background tasks should be utilized as well.
* Try to work on no more than 2 issues at a time. Ideally it should be just 1.
* Checkout-implement-test-submit.

Once every week there is a half-hour team meeting. Preferably Tuesdays or Wednesdays.

Once every week have a one-on-one half an hour with your manager. Helps bring up more private issues.

Once every month we have a 2 hours all hands session. Anything can be raised by anyone.

### How often is code releazed?
We use Continuos Deployment using Jenkins. As we try to break issues into smaller parts, code can be released very frequently. We aim for multiple times a day.

### What is the development process from code's perspective?
Code gets checked out and developed locally by picking a bug/feature from the issue list. The development could be pair-programming or alone. The developed code is also tested and coverage calculated. Code gets submitted for code review and additional verification (static code analysis, integration testing). If they all pass, Code gets merged to the master branch. Master is build on CI server and pushed to a staging server. A load balancer linearly starts redirecting some trafic to staging server and backtracks rapidly on any server errors. Eventually staging server gets 100% traffic, gets renamed to production server and previous production server becomes staging.

### What is the testing culture? Do we have Unit/integration tests? What does a QA process look like?
Some teams can practice Test-Driven Development but it's not required. People think differently and some like to first do tests, other don't. Sometimes test are not too clear if we start with tests. Eventually all code should be unit tested and some smaller amount of functional and integration testing is done to verify the output from user's perspective. We aim for at least 85-90% code coverage and a build fails if it is below that level.

### How teams work? What sort of sw develoment process/methodology? Any agile methodologies enforced, recommended or practiced?
Each team can decide for itself - nothing is enforced. Agile methodlogies like Scrum, XP and Kanban are recommended but teams work differently as people are different.

### How the team communicates and collaborates?
We use Google Hangouts for communication.

### What do we use for source control?
[Git](https://git-scm.com/). It's not the easiest learning curve, but it's the most used out there, it allows you to easily experiment and revert which complies with our Scientific way of development.

### What do you use for bug/task tracker?

### How do you define configuration in different environments (dev/test/prod)?

### How do you isolate processes?

### Do we do code reviews? What is the process?
Either pair-programming or code review is a necessary condition for commiting code. 2 more eyeballs can catch a lot more errors especially when your own ego isn't involved.

### How do we prioritize features vs. bugs (new development vs. fixing existing code)?
Generally you want to fix bugs before writing new code. [The Joel Test](http://www.joelonsoftware.com/articles/fog0000000043.html).

### What is the up-to-date schedule and where can I find it?
Having a schedule forces you to plan and prioritize features and stay on the same page as the rest of the business. [The Joel Test](http://www.joelonsoftware.com/articles/fog0000000043.html). We use Google Calendar to put organize dates.

### Do you spec out features before building them? How?
Finding and fixing problems is dramatically easier in the design stage.  Specs save time and frustration. [The Joel Test](http://www.joelonsoftware.com/articles/fog0000000043.html)

### What is the work environment? Noise levels? Interruptions?
Quiet space and privacy have well-documented productivity benefits. We don't like open space, sorry. We find it too distracting for work. There are common areas you can go and hang out but when you work, you (and potentially your pair-programmer) are isolated. [The Joel Test](http://www.joelonsoftware.com/articles/fog0000000043.html)

### How do we do UX / usability testing?
Grabbing five or six people in the hallway is a good start.  User studies are even better. [The Joel Test](http://www.joelonsoftware.com/articles/fog0000000043.html)

### Do we do design reviews? Before writing code?
In all but the smallest of companies and tasks, getting input from others before starting can save time and effort. Studies show that making changes post-delivery is 5x (for small projects) to >100X (for large projects) more expensive than during requirements definition.

### Are there all-hands meetings? How do we ensure people's voices are heard, valued and respected?
[Research](https://rework.withgoogle.com/blog/five-keys-to-a-successful-google-team/) shows the most important factor in team effectiveness is psychological safety, a "shared belief held by members of a team that the team is safe for interpersonal risk-taking."  One component of this is conversational turn-taking, or that everyone talks roughly the same amount.

### How are you chosing the software tools? What do you value in them?
We want tools that have stood the test of time, are still in wide use and are actively deloped. We acknoledge that this requirement is hard to follow since new tools appear all the time and the hype is sometimes hard to ignore. But the rationale is - if the tool is relatively new and in active development - unexpected errors will pop up that nobody has dealt with in the edge cases. This may take time to get fixed if at all and it will probably bring new errors.

We also prefer open sourced software. Companies go out of business all the time. If the tool is good and people use it, people help it grow.

In general, use the version before the latest stable - that is about 1 year old. That ensures that the version is being tested and there are enough stackoverflow articles about it.

| Software  | Years since release  | Risk of unexpected breaking |
|---|---|
| Vim | 1991, 24 years | Low |
| PostgreSQL  | 1996, 19 years  | Low |
| Nagios | 1999, 17 years | Low |
| Eclipse | 2001, 14 years | Low |
| Ubuntu | 2004, 11 years | Low |
| Nginx | 2004, 11 years | Low |
| Git | 2005, 11 years | Low |
| RabbitMQ | 2007, 9 years | Low |
| Virtualbox | 2007, 9 years | Low |
| JQuery | 2006, 9 years | Low |
| Jenkins (forked from Hudson) | 2011, 4 years (2004, 12 years) | Low |
| Gerrit | 2009, 7 years | Low |
| Flask | 2010, 6 years | Medium |
| Vagrant  | 2010, 6 years  | Medium |
| PyCharm | 2010, 5 years | Medium |
| GitLab | 2011, 5 years | Medium |
| Ansible  | 2012, 4 years  | Medium |
| Docker  | 2013, 3 years  | High |
| Atom | 2014, 2 years | High |

### Do we do hackatons/20% time projects etc? How about contributing to open source?
We acknoledge that in a rapidly moving programming environment people have different interests which change over time. We are following a similar to Google 20% project time - you can work on whatever you want 1 day of the week as long as you are not the only person working on that project (i.e. find a buddy within the organization).

### How do we make technical hiring decisions?
This is important because it helps you see what people you are going to work with. Five or six technical interviewers vote via secret ballot; all must agree (except perhaps one junior engineer), or it's a no-hire.  No one should be able to hire unilaterally or override the vote of someone else; everyone should have unilateral veto power. The cost of a poor hire is far greater than the cost of missing a good hire.

### How do we monitor metrics?

### What metrics are we monitoring?

### How are we leanly validating ideas?