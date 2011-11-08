import sqlparse
from django.db.models import Q
import re

# TODO!!
# Support Integer searches
def parse(raw_sql, allowed_models):
    operator_map = {
        "="     : "exact",
        "<"     : "lt",
        "<="    : "lte",
        ">"     : "gt",
        ">="    : "gte",
        "!="    : "exact"
    }

    raw_sql = re.sub(r'\s\'([^\s])\'\s?', r' "\1"', raw_sql)

    print "RAW SQL: %s" % raw_sql

    token_list = sqlparse.parse(raw_sql)[0]
    
    def gather_search_part(comparison_token_list):
        print "Comparison List: %s" % comparison_token_list.tokens

        search_token = comparison_token_list.token_next_by_instance(0, sqlparse.sql.Identifier)

        print "Search Token: %s" % search_token

        equality_token = comparison_token_list.token_next_by_type(comparison_token_list.token_index(search_token), sqlparse.tokens.Comparison)
        
        print "Equality Token: %s" % equality_token

        value_token = comparison_token_list.token_next_by_instance(comparison_token_list.token_index(equality_token), (sqlparse.sql.Identifier, sqlparse.sql.Comment, ))
        
        print "Value Token: %s" % value_token

        equality_token_value = equality_token.to_unicode()

        operator = operator_map.get(equality_token_value, '')

        q_search = ("%s__%s" % (search_token.to_unicode(), operator)).encode('utf-8')

        # Needed to replace quotations, as the strings unicoded rendition is encased by them
        if equality_token_value == "!=":
            return ~Q(**{q_search:value_token.to_unicode().replace('\"','')})
        else:
            return Q(**{q_search:value_token.to_unicode().replace('\"','')})

    def get_joining_operator(token_list, index):
        conjunction_token = token_list.token_next_by_type(index, sqlparse.tokens.Keyword)

        if conjunction_token:
            if conjunction_token.to_unicode() == 'AND':
                joining_operator = Q.AND
            elif conjunction_token.to_unicode() == 'OR':
                joining_operator = Q.OR
            else:
                joining_operator = None
        else:
            joining_operator = None
        
        return (conjunction_token, joining_operator, )

    def discover_model():
        from_token = token_list.token_next_match(0, sqlparse.tokens.Keyword, 'FROM')

        next_token = token_list.token_next(from_token)

        model_name = next_token.get_name()

        for allowed_model in allowed_models:
            if allowed_model.__name__.lower() in model_name.lower():
                return allowed_model
        
        return None

    # WHERE email_address = "123@test.com" OR (email_address = "456@test.com" AND first_name = "Bryan")
    def iterate_comparisons(token_list):
        print "Where List!"
        print token_list.tokens

        child_list = token_list.token_next_by_instance(0, (sqlparse.sql.Comparison, sqlparse.sql.Parenthesis, ))

        print "CHILD LIST: %s" % child_list
        print "CHILD INSTANCE: %s" % child_list.__class__

        q = Q()

        joining_operator = None

        while child_list:
            print "START LOOP" 

            if isinstance(child_list, sqlparse.sql.Comparison):
                search_part = gather_search_part(child_list)

                print "SEARCH PART: %s" % search_part

                if joining_operator:
                    q.add(search_part, joining_operator)
                else:
                    q = search_part

            elif isinstance(child_list, sqlparse.sql.Parenthesis):
                print "PARENTHESIS"

                if joining_operator:
                    q.add(iterate_comparisons(child_list), joining_operator)
                else:
                    q = iterate_comparisons(child_list)

            print "Defined q: %s " % q

            conjunction_token, joining_operator = get_joining_operator(token_list, token_list.token_index(child_list))

            print "Defined q: %s " % q
            print "CONJUNCTION_TOKEN %s" % conjunction_token

            # No additional conjunctions discovered, break out of loop
            if not conjunction_token:
                break

            token_index = token_list.token_index(conjunction_token)

            child_list = token_list.token_next_by_instance(token_index, (sqlparse.sql.Comparison, sqlparse.sql.Parenthesis, ))
        
        return q
    
    print token_list.tokens

    select_token = token_list.token_first()

    if select_token.ttype != sqlparse.keywords.KEYWORDS_COMMON['SELECT']:
        raise Exception("Not a valid SELECT query!")

    next_token = token_list.token_next(select_token)

    if isinstance(next_token, sqlparse.sql.IdentifierList):
        print "Identifier list"
    elif next_token.match(sqlparse.tokens.Wildcard, "*"):
        print "Wildcard"
    
    model = discover_model()

    if not model:
        raise Exception("Unsupported Model Associated!")

    print "Discovered Model %s" % model
    
    # Handle search criteria
    where_list = token_list.token_next_by_instance(token_list.token_index(next_token), sqlparse.sql.Where)

    if where_list:
        q = iterate_comparisons(where_list)

        print "FINAL Q: %s" % q

        query_set = model.objects.filter(q)
    else:
        query_set = model.objects.all()

    return query_set