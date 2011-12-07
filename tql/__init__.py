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
    
    def gather_search_part(key_token, equality_token, value_token, negate = False):
        print "NEGATE? : %s" % negate

        field_value = key_token.to_unicode()
        search_value = value_token.to_unicode().replace('\"','')

        if equality_token.match(sqlparse.tokens.Keyword, "IS"):
            q_search = ("%s__isnull" % field_value).encode('utf-8')

            search_value = search_value == 'NULL'
        if equality_token.match(sqlparse.tokens.Keyword, "LIKE"):
            start_wildcard = search_value.startswith('%')
            end_wildcard = search_value.endswith('%')

            search_value = search_value.replace('%', '')

            if start_wildcard and end_wildcard:
                operator = 'contains'
            elif start_wildcard:
                operator = 'endswith'
            elif end_wildcard:
                operator = 'startswith'
            else:
                operator = 'exact'

            q_search = ("%s__%s" % (field_value, operator)).encode('utf-8')

        elif equality_token.match(sqlparse.tokens.Comparison, operator_map.keys()):
            operator = operator_map.get(equality_token.value, '')

            q_search = ("%s__%s" % (field_value, operator)).encode('utf-8')

        # Needed to replace quotations, as the strings unicoded rendition is encased by them
        if equality_token.value == "!=" or negate:
            return ~Q(**{q_search:search_value})
        else:
            return Q(**{q_search:search_value})

    # WHERE email_address = "123@test.com" OR (email_address = "456@test.com" AND first_name = "Bryan")
    def iterate_token_list(token_list, q = None):
        print token_list.tokens

        index = 0

        if not q:
            q = Q()
        
        joining_operator = None

        while True:
            tokens = [
                token_list.token_next_match(index, sqlparse.tokens.Keyword, ["LIKE", "NOT", "IS"]),
                token_list.token_next_match(index, sqlparse.tokens.Comparison , operator_map.keys()),
                token_list.token_next_by_instance(index, sqlparse.sql.Comparison),
                token_list.token_next_by_instance(index, sqlparse.sql.Parenthesis)
            ]

            min_index = 9999999999999
            token = None

            for index in range(len(tokens)):
                if tokens[index]:
                    current_index = token_list.token_index(tokens[index])

                    min_index = min(min_index, current_index)

                    if min_index == current_index:
                        token = tokens[index]

            # if isinstance(token, sqlparse.tokens.Keyword):
            if token:
                if token.ttype in [sqlparse.tokens.Keyword, sqlparse.tokens.Comparison]:
                    index = token_list.token_index(token)

                    if token.value.upper() == 'NOT':
                        (key_token, token, value_token) = (token_list.token_prev(index), token_list.token_next(index + 1), token_list.token_next(index + 2))
                    else:
                        (key_token, value_token) = (token_list.token_prev(index), token_list.token_next(index))

                    q_object = gather_search_part(key_token, token, value_token, token.value.upper() == 'NOT')

                    index = token_list.token_index(value_token)
                elif isinstance(token, sqlparse.sql.Comparison) or isinstance(token, sqlparse.sql.Parenthesis):
                    q_object = iterate_token_list(token, q)

                    index = token_list.token_index(token)
                else:
                    break
            else:
                break
            
            if joining_operator:
                q.add(q_object, joining_operator)
            else:
                q = q_object
            
            conjunction_token, joining_operator = get_joining_operator(token_list, index)

            if not joining_operator:
                break

            # Move onto the next element
            index += 1
        
        return q

    raw_sql = re.sub(r'\s\'([^\s])\'\s?', r' "\1"', raw_sql)

    print "RAW SQL: %s" % raw_sql

    token_list = sqlparse.parse(raw_sql)[0]
    
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
    current_index = token_list.token_index(next_token)

    where_list = token_list.token_next_by_instance(current_index, sqlparse.sql.Where)
    order_by = token_list.token_next_match(current_index, sqlparse.tokens.Keyword, ["ORDER"])
    limit_token = token_list.token_next_match(current_index, sqlparse.tokens.Keyword, "LIMIT")

    if where_list:
        q = iterate_token_list(where_list)

        print "FINAL Q: %s" % q

        query_set = model.objects.filter(q)
    else:
        query_set = model.objects.all()
    
    if order_by:
        current_index = token_list.token_index(order_by)

        field_ordering = []

        while True:
            field_token = token_list.token_next_by_instance(current_index, sqlparse.sql.Identifier)

            if not field_token:
                break
            
            field_value = field_token.to_unicode()
            
            order_token = token_list.token_next_match(current_index, sqlparse.tokens.Keyword, ["ASC", "DESC"])

            if order_token and order_token.value.upper() == 'DESC':
                field_value = '-' + field_value
            
            field_ordering.append(field_value)

            current_index = token_list.token_index(order_token or field_token) + 1
        
        query_set = query_set.order_by(*field_ordering)
    
    if limit_token:
        current_index = token_list.token_index(limit_token)

        identifier = token_list.token_next_by_type(current_index, sqlparse.tokens.Number)

        if identifier:
            query_set = query_set[:int(identifier.value)]
        else:
            identifier_list = token_list.token_next_by_instance(current_index, sqlparse.sql.IdentifierList)

            if identifier_list:
                offset_token = identifier_list.token_next_by_type(0, sqlparse.tokens.Number)

                limit_token = identifier_list.token_next_by_type(identifier_list.token_index(offset_token), sqlparse.tokens.Number)

                offset = int(offset_token.value)
                limit = offset + int(limit_token.value)

                query_set = query_set[offset:limit]

    return query_set