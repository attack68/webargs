from webargs.core import json
from flask import Flask, jsonify as J, Response, request
from flask.views import MethodView

import marshmallow as ma
from webargs import fields
from webargs.flaskparser import parser, use_args, use_kwargs
from webargs.core import MARSHMALLOW_VERSION_INFO


class TestAppConfig:
    TESTING = True


hello_args = {"name": fields.Str(missing="World", validate=lambda n: len(n) >= 3)}
hello_multiple = {"name": fields.List(fields.Str())}


class HelloSchema(ma.Schema):
    name = fields.Str(missing="World", validate=lambda n: len(n) >= 3)


strict_kwargs = {"strict": True} if MARSHMALLOW_VERSION_INFO[0] < 3 else {}
hello_many_schema = HelloSchema(many=True, **strict_kwargs)

app = Flask(__name__)
app.config.from_object(TestAppConfig)


@app.route("/echo", methods=["GET", "POST"])
def echo():
    return J(parser.parse(hello_args))


@app.route("/echo_query")
def echo_query():
    return J(parser.parse(hello_args, request, locations=("query",)))


@app.route("/echo_use_args", methods=["GET", "POST"])
@use_args(hello_args)
def echo_use_args(args):
    return J(args)


@app.route("/echo_use_args_validated", methods=["GET", "POST"])
@use_args({"value": fields.Int()}, validate=lambda args: args["value"] > 42)
def echo_use_args_validated(args):
    return J(args)


@app.route("/echo_use_kwargs", methods=["GET", "POST"])
@use_kwargs(hello_args)
def echo_use_kwargs(name):
    return J({"name": name})


@app.route("/echo_multi", methods=["GET", "POST"])
def multi():
    return J(parser.parse(hello_multiple))


@app.route("/echo_many_schema", methods=["GET", "POST"])
def many_nested():
    arguments = parser.parse(hello_many_schema, locations=("json",))
    return Response(json.dumps(arguments), content_type="application/json")


@app.route("/echo_use_args_with_path_param/<name>")
@use_args({"value": fields.Int()})
def echo_use_args_with_path(args, name):
    return J(args)


@app.route("/echo_use_kwargs_with_path_param/<name>")
@use_kwargs({"value": fields.Int()})
def echo_use_kwargs_with_path(name, value):
    return J({"value": value})


@app.route("/error", methods=["GET", "POST"])
def error():
    def always_fail(value):
        raise ma.ValidationError("something went wrong")

    args = {"text": fields.Str(validate=always_fail)}
    return J(parser.parse(args))


@app.route("/echo_headers")
def echo_headers():
    return J(parser.parse(hello_args, locations=("headers",)))


@app.route("/echo_cookie")
def echo_cookie():
    return J(parser.parse(hello_args, request, locations=("cookies",)))


@app.route("/echo_file", methods=["POST"])
def echo_file():
    args = {"myfile": fields.Field()}
    result = parser.parse(args, locations=("files",))
    fp = result["myfile"]
    content = fp.read().decode("utf8")
    return J({"myfile": content})


@app.route("/echo_view_arg/<view_arg>")
def echo_view_arg(view_arg):
    return J(parser.parse({"view_arg": fields.Int()}, locations=("view_args",)))


@app.route("/echo_view_arg_use_args/<view_arg>")
@use_args({"view_arg": fields.Int(location="view_args")})
def echo_view_arg_with_use_args(args, **kwargs):
    return J(args)


@app.route("/echo_nested", methods=["POST"])
def echo_nested():
    args = {"name": fields.Nested({"first": fields.Str(), "last": fields.Str()})}
    return J(parser.parse(args))


@app.route("/echo_nested_many", methods=["POST"])
def echo_nested_many():
    args = {
        "users": fields.Nested({"id": fields.Int(), "name": fields.Str()}, many=True)
    }
    return J(parser.parse(args))


@app.route("/echo_nested_many_data_key", methods=["POST"])
def echo_nested_many_with_data_key():
    data_key_kwarg = {
        "load_from" if (MARSHMALLOW_VERSION_INFO[0] < 3) else "data_key": "X-Field"
    }
    args = {"x_field": fields.Nested({"id": fields.Int()}, many=True, **data_key_kwarg)}
    return J(parser.parse(args))


class EchoMethodViewUseArgs(MethodView):
    @use_args({"val": fields.Int()})
    def post(self, args):
        return J(args)


app.add_url_rule(
    "/echo_method_view_use_args",
    view_func=EchoMethodViewUseArgs.as_view("echo_method_view_use_args"),
)


class EchoMethodViewUseKwargs(MethodView):
    @use_kwargs({"val": fields.Int()})
    def post(self, val):
        return J({"val": val})


app.add_url_rule(
    "/echo_method_view_use_kwargs",
    view_func=EchoMethodViewUseKwargs.as_view("echo_method_view_use_kwargs"),
)


@app.route("/echo_use_kwargs_missing", methods=["post"])
@use_kwargs({"username": fields.Str(required=True), "password": fields.Str()})
def echo_use_kwargs_missing(username, **kwargs):
    assert "password" not in kwargs
    return J({"username": username})


# Return validation errors as JSON
@app.errorhandler(422)
@app.errorhandler(400)
def handle_error(err):
    if err.code == 422:
        assert isinstance(err.data["schema"], ma.Schema)
    return J(err.data["messages"]), err.code
