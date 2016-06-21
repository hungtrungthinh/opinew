## API Design

`Resource` is a thing like shop|review|product|user etc. We use plurals in the URL definition and singular in model definition.

`Action` is an action that is performed on a `resource`. Actions can change things on the resource or query for a specific resource or a list of resources.

Filters and queries are added as GET parameters.

Payload parameters are added as POST parameters.

**Example Resources**
* user - users
* product - products
* review - reviews
* shop - shops
* platform - platforms
* question - questions
* answer - answers

Addtionally resources, like the `plugins` for example doesn't necessarily need to have a corresponding model.

**Example Actions**
* users/login
* products/search
* reviews/create
* reviews/34/like

### General rules for the routes
Can be broken occasionally but try to stick to them.

Get all resources:

    GET  /resources

Get single resource by id:

    GET  /resources/<id>

Execute idempotent action on all resource (e.g. search all reviews):

    GET  /resources/action

Execute idempotent action on single resource (e.g. search within product):

    GET  /resources/<id>/action

Execute action on single resource (e.g. create review, like review)

    POST /resources/<id>/act

Get sub_resources for resource_id (e.g. products/1/reviews)

    GET  /resources/<id>/sub_resources

Execute idempotent action on single sub_resource of resource
    GET  /resources/<id>/sub_resources/act

Execute action on single sub_resource of resource

    POST /resources/<id>/sub_resources/act

## Marketing routes
### Get main marketing page

    GET /

**Access**
Public

**Parameters**
None

**Request context**
* Renders `index.html`

**Asyncronous context**
None

## User routes
### User register render

    GET /users/register

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
* None

### User create

    POST /users/create

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
* None

### User login render

    GET /users/login

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
* None

### User login action

    POST /users/login

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
* None

### View User profile

    GET /users/<id>

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
* None

### User logout

    POST /users/logout

**Access**
* Logged in user

**Parameters**
*

**Request context**
*

**Asyncronous context**
* None

## Shopify routes
### Install Shopify plugin

    GET /platforms/shopify/shops/create

**Access**
Public

**Parameters**
  * `shop` - must end in `.myshopify.com`

**Request context**
* Redirect to `<shop_domain>/admin/oauth/authorize`

**Asyncronous context**
* None

### Callback after user has accepted permissions on Shopify plugin

    GET /platforms/shopify/shops/callback

**Access**
Public

**Parameters**
  * `state`
  * `hmac`
  * `shop`  - must end in `.myshopify.com`
  * `code`

**Request context**
* Verify the required parameters.
* If everything is successful, initialize the Shopify API by requesting an access token.
* Create a temporary user and log in. Send the logged in user_id to a queue.
* Create a shop with owner the logged in user and save the access token.
* Redirect to `/shop/<id>/plugin_setup` for setup plugin instructions.

**Asyncronous context**
* *Parameters*:
  * user_id
* Request shop owner details from Shopify API
* Update the user in our database.
* Setup Shopify webhooks on product create/modify/delete, order create/delete and application uninstall.
* Request products from Shopify API and update in our database.
* Request orders from Shopify API and update in our database.
* Send an email with a temporary password

## Plugin routes
### Get plugin for product

    GET /plugins/product

**Access**
* Public
* Usually embedded in an iframe

**Parameters**
* get_by - either platform_product_id | url
* platform_product_id (if get_by==platform_product_id)
  * The product_id defined by the platform e.g. shopify
* url (if get_by==url)
  * The URL from which the plugin has been called. Accept all combinations of http/https, www. or no, ending slash or no. Also try to accept basic form of regex.

**Request context**
* Render `plugins/product.html` with all reviews about the specified product.

**Asyncronous context**
None

### Get plugin for shop

    GET /plugins/shop

**Access**
* Public
* Usually embedded in an iframe

**Parameters**
* get_by - either shop_id | url
* shop_id (if get_by==shop_id)
  * The product_id defined by the platform e.g. shopify
* url (if get_by==url)
  * The URL from which the plugin has been called. Accept all combinations of http/https, www. or no, ending slash or no. Also try to accept basic form of regex.

**Request context**
* Render `plugins/shop.html` with all reviews about the specified product.

**Asyncronous context**
None


### Aggregate star rating for a product plugin

    GET /plugins/product/aggregate-rating

**Access**
* Public
* Usually embedded in an iframe

**Parameters**
* get_by - either platform_product_id | url
* platform_product_id (if get_by==platform_product_id)
  * The product_id defined by the platform e.g. shopify
* url (if get_by==url)
  * The URL from which the plugin has been called. Accept all combinations of http/https, www. or no, ending slash or no. Also try to accept basic form of regex.

**Request context**
* Render `plugins/product.html` with all reviews about the specified product.

**Asyncronous context**
None

## Reviews
### Create a review about a product

    POST /products/<id>/reviews/create

**Acess**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
None

### Create a review about a shop

    POST /shops/<id>/reviews/create

**Acess**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
None

### Render a single review page. Used for sharing on social networks.

    GET /reviews/<id>

**Acess**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
None

### Render a review that a user owns, update the review

    GET /reviews/<id>/edit

**Access**
* User logged in and owning the review <id>

**Parameters**
*

**Request context**
*

**Asyncronous context**
None

### Update a review that a user owns

    POST /reviews/<id>/edit

**Access**
* User logged in and owning the review <id>

**Parameters**
*

**Request context**
*

**Asyncronous context**
None

### Delete a review that a user owns

    POST /reviews/<id>/delete

**Access**
* User logged in and owning the review <id>

**Parameters**
*

**Request context**
*

**Asyncronous context**
None

## Main website
### Get reviews for a shop
Reviews for shop. Link to this if javascript can't load the plugin and for SEO.

    GET /shops/<id>/reviews

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### Get reviews for a product
Reviews for shop. Link to this if javascript can't load the plugin and for SEO.

    GET /products/<id>/reviews

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

## Questions and answers
### Create a question to a product

  POST /products/<id>/questions/create

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### Render the question id

    GET /questions/<id>

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### Create an answer for a question

    POST /questions/<id>/answers/create

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### Retrieve results for reviews (and questions) about a product

    GET /products/<id>/reviews/search

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### Create a comment to a review

    GET /reviews/<id>/comments/create

**Access**
* Public

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### asynchronous log of events - requires javascript

    POST /logs

**Access**
* Public

**Parameters**
* session_id=XXXX; object=plugin|review; action=load|glimpse|hover|click

**Request context**
*

**Asyncronous context**
*

## Shop Dashboard
### View aggregation of reviews

    GET /shop/<id>/dashboard/reviews

**Access**
* Logged in shop owner

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### View aggregation of question

    GET /shop/<id>/dashboard/questions

**Access**
* Logged in shop owner

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### View aggregation of shop analytics

    GET /shop/<id>/dashboard/analytics

**Access**
* Logged in shop owner

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### View customer account details

    GET /shop/<id>/dashboard/account

**Access**
* Logged in shop owner

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### View shop settings

    GET /shop/<id>/dashboard/settings

**Access**
* Logged in shop owner

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### View actions to be taken now by the shop owner (change pwd/respond to review etc)

    GET /shop/<id>/dashboard/incomming

**Access**
* Logged in shop owner

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### View scheduled actions for this shop

    GET /shop/<id>/dashboard/scheduled

**Access**
* Logged in shop owner

**Parameters**
*

**Request context**
*

**Asyncronous context**
*

### View instructions for setting up a plugin

    GET /shop/<id>/plugin_setup

**Access**
* Logged in shop owner

**Parameters**
*

**Request context**
*

**Asyncronous context**
*