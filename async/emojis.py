import requests

COUNT = 20

r = requests.get("http://emojitracker.com/api/rankings")
j = r.json()

for emoji_ranking in j[:COUNT]:
    print u'<span class="emoji-keyboard">%s</span>' % emoji_ranking['char']

print "-------------"

for emoji_ranking in j[:COUNT]:
    r = requests.get("http://emojitracker.com/api/details/" + emoji_ranking['id'])
    j = r.json()
    print "':%s:': '%s.png'," % (j['char_details']['short_name'], emoji_ranking['id'].lower())
