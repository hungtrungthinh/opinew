function hookSettings (){
    $('#nav-opinew-diamond').click(function () {
        $.ajax({
            url: '/reviews',
            headers: {"mobile": "true"},
            type: 'GET',
            success: function (response) {
              $('#content-wrapper').html(response);
            }
        });
    });
}

function hookNewsFeed (){
    $('#nav-settings-btn').click(function () {
        $.ajax({
            url: '/settings',
            headers: {"mobile": "true"},
            type: 'GET',
            success: function (response) {
              $('#content-wrapper').html(response);
            }
        });
    });
}

function hookNotifications (){
    $('#nav-notifications-btn').click(function () {
        $.ajax({
            url: '/notifications',
            headers: {"mobile": "true"},
            type: 'GET',
            success: function (response) {
              $('#content-wrapper').html(response);
            }
        });
    });
}

function hookUserProfile (){
    $('#nav-user-profile-btn').click(function () {
        $.ajax({
            url: '/user_profile',
            headers: {"mobile": "true"},
            type: 'GET',
            success: function (response) {
              $('#content-wrapper').html(response);
            }
        });
    });
}

$(document).ready(function () {
    hookNewsFeed();
    hookSettings();
    hookNotifications();
    hookUserProfile();
});