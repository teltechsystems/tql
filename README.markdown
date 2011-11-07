This library allows supplying a SQL query and a list of models allowed to query on and return a query object. It is similar to Facebook's [FQL](http://developers.facebook.com/docs/reference/fql/)

Usage
-----

    from tql import tqlparse
    allowed_models = (MyModel, MyModel2, MyModel3)
    sql = "SELECT * FROM MyModel WHERE first_name = 'John'"
    q = tqlparse.parse(sql, allowed_models))

