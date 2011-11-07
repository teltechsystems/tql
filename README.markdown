This library allows supplying a SQL query and a list of models allowed to query on and return a query object. It is similar to Facebook's [FQL](http://developers.facebook.com/docs/reference/fql/)

Usage
-----

    import tql
    from records.models import Call, DID
    allowed_models = [Call, DID]
    sql = "SELECT * FROM Call WHERE status = 'in-progress'"
    q = tql.parse(sql, allowed_models)

