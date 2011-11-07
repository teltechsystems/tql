TelTech Query Language
======================

This library provides the ability to perform an end-user SQL query on a list of Django models. It is similar to Facebook's [FQL](http://developers.facebook.com/docs/reference/fql/).

Usage
-----

    import tql
    from records.models import Call, DID
    allowed_models = [Call, DID]
    sql = "SELECT * FROM Call WHERE status = 'in-progress'"
    q = tql.parse(sql, allowed_models)

