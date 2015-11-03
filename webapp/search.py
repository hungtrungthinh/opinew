import re
from webapp.models import Company, Review, User


def highlight(query, text):
    snippets = []
    for word in query.split():
        match_positions = [m.start() for m in re.finditer(word, text)]
        for mpos in match_positions:
            match_before = ' '.join(text[:mpos].split()[-5:])
            match = text[mpos:mpos + len(word)]
            match_after = ' '.join(text[mpos:].split()[1:5])
            snippet = "%s <b>%s</b> %s" % (match_before, match, match_after)
            snippets.append(snippet)
    return '...'.join(snippets)


def in_field(query, field):
    if field and query in field.lower():
        return highlight(query, field.lower())
    return None


def create_user_result(query, user):
    result = {
        'type': 'user',
        'user': user,
        'match': {}
    }
    match = dict()
    match_name = in_field(query, user.name)
    if match_name:
        match['user_name'] = match_name
    match_help = in_field(query, user.can_help_with)
    if match_help:
        match['user_can_help_with'] = match_help
    result['match'] = match
    return result


def create_review_result(query, review):
    result = {
        'type': 'review',
        'review': review,
        'match': {}
    }
    match = dict()
    match_body = in_field(query, review.body)
    if match_body:
        match['review_body'] = match_body
    result['match'] = match
    return result


def create_company_result(query, company):
    result = {
        'type': 'company',
        'company': company,
        'company_team': [],
        'match': {},
    }
    match = dict()
    match['company_name'] = in_field(query, company.name)
    match['company_description'] = in_field(query, company.description)
    match['company_industry'] = in_field(query, company.industry)
    match['company_one_min_pitch'] = in_field(query, company.one_min_pitch)
    result['match'] = match
    for member in company.team:
        member_result = create_user_result(query, member)
        if member_result['match']:
            result['company_team'].append(member_result)
    return result


def query_company(query):
    company_results = Company.query.search(query).all()
    results = []
    for company in company_results:
        result = create_company_result(query, company)
        results.append((result, 0))
    return results


def query_user(query):
    user_results = User.query.search(query).all()
    results = []
    for user in user_results:
        result = create_user_result(query, user)
        results.append((result, 0))
    return results


def query_review(query):
    review_results = Review.query.search(query).all()
    results = []
    for review in review_results:
        result = create_review_result(query, review)
        results.append((result, 0))
    return results


def rank_results(results):
    sorted_results = sorted(results, key=lambda x: x[1])
    return [s[0] for s in sorted_results]


def search_and_rank(query):
    query = query.lower()
    results = []
    results += query_company(query)
    results += query_user(query)
    results += query_review(query)
    results = rank_results(results)
    return results
