TelTech Query Language
======================

This library provides the ability to perform an end-user SQL query on a list of Django models. It is similar to Facebook's [FQL](http://developers.facebook.com/docs/reference/fql/).

Usage
-----

    import tql
    from records.models import Call, DID
    
    allowed_models = [Call, DID]
    sql = "SELECT * FROM `Call` WHERE status = 'in-progress'"
    q = tql.parse(sql, allowed_models)
    
    # Do stuff with q, a QuerySet object
    total = q.count()
    q = q.filter(account__sid="AC8f9808f97fa04ddb922fc02e805fc091")
    
    for call in q:
        # Do something
        pass

