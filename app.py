#! /usr/bin/env python3
#
# Copyright (c) 2017 Torchbox Ltd.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely. This software is provided 'as-is', without any express or implied
# warranty.

from flask import Flask, request, jsonify, Response
import sys
import ldap
import logging

logger = logging.getLogger('kube-ldap-authn')
logger.setLevel(logging.INFO)
hdl = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)-8s] %(name)-15s: %(message)s')
hdl.setFormatter(formatter)
logger.addHandler(hdl)


class Failure(Exception):
    pass


app = Flask('kube-ldap-authn')

try:
    app.config.from_envvar('KUBE_LDAP_AUTHN_SETTINGS')
except RuntimeError as e:
    logger.error(str(e))
    sys.exit(1)

if 'LDAP_TLS_CA_FILE' in app.config:
    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, app.config['LDAP_TLS_CA_FILE'])
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)


@app.route('/healthz', methods=['GET'])
def healthz():
    return Response("OK\n", mimetype='text/plain')


AUTH_ERROR = jsonify({
    'apiVersion': 'authentication.k8s.io/v1beta1',
    'kind': 'TokenReview',
    'status': {
        'authenticated': False,
    },
})


def check_request_valid(request):
    req = request.json
    if req is None:
        raise Failure("invalid or missing request json")

    for field in ('apiVersion', 'kind', 'spec'):
        if req.get(field) is None:
            raise Failure("missing {}".format(field))

    supported_api = ('authentication.k8s.io/v1beta1')

    if req['apiVersion'] not in supported_api:
        raise Failure("apiVersion: {} not supported".format(req['apiVersion']))

    if req['kind'] != 'TokenReview':
        raise Failure("kind: {} not supported".format(req['kind']))

    if req['spec'].get('token'):
        raise Failure("invalid spec")


def get_ldap_connection():
    try:
        ld = ldap.initialize(app.config['LDAP_URL'])
    except ldap.LDAPError as e:
        raise Failure("LDAP connection error: " + str(e))

    ld.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

    if app.config.get('LDAP_START_TLS', True):
        try:
            ld.start_tls_s()
        except ldap.LDAPError as e:
            raise Failure("LDAP TLS error: " + str(e))

    try:
        ld.simple_bind_s(app.config['LDAP_BIND_DN'],
                         app.config['LDAP_BIND_PASSWORD'])
    except ldap.LDAPError as e:
        raise Failure("LDAP bind error: " + str(e))

    return ld


def search_user(ld, user_search):
    try:
        r = ld.search_s(app.config['LDAP_USER_SEARCH_BASE'],
                        ldap.SCOPE_SUBTREE, user_search, [
                            app.config['LDAP_USER_NAME_ATTRIBUTE'],
                            app.config['LDAP_USER_UID_ATTRIBUTE']
                        ])
    except ldap.LDAPError as e:
        logger.info("LDAP search error: " + str(e))
        return AUTH_ERROR

    if len(r) != 1:
        logger.info("expected 1 user, found " + str(len(r)))
        return AUTH_ERROR


@app.route('/authn', methods=['POST'])
def authn():
    try:
        check_request_valid(request.json)
        ld = get_ldap_connection()
    except Failure as e:
        logger.info(e)
        return AUTH_ERROR

    token = request.json['spec']['token']
    escaped_token = ldap.filter.escape_filter_chars(token)
    user_search = app.config['LDAP_USER_SEARCH_FILTER'].format(escaped_token)

    try:
        r = search_user(ld, user_search)
    except Failure as e:
        logger.info(e)
        return AUTH_ERROR

    username = r[0][1][app.config['LDAP_USER_NAME_ATTRIBUTE']][0].decode('ascii')
    uid = r[0][1][app.config['LDAP_USER_UID_ATTRIBUTE']][0].decode('ascii')

    username_escaped = ldap.filter.escape_filter_chars(username)
    dn_escaped = ldap.filter.escape_filter_chars(r[0][0])

    group_search = app.config['LDAP_GROUP_SEARCH_FILTER'].format(username_escaped, dn_escaped)
    try:
        g = ld.search_s(app.config['LDAP_GROUP_SEARCH_BASE'],
                        ldap.SCOPE_SUBTREE, group_search,
                        [app.config['LDAP_GROUP_NAME_ATTRIBUTE']])
    except ldap.LDAPError as e:
        logger.info("LDAP search error: " + str(e))
        return AUTH_ERROR

    groups = [
        i[1][app.config['LDAP_GROUP_NAME_ATTRIBUTE']][0].decode('ascii')
        for i in g
    ]

    return jsonify({
        'apiVersion': 'authentication.k8s.io/v1beta1',
        'kind': 'TokenReview',
        'status': {
            'authenticated': True,
            'user': {
                'username': username,
                'uid': uid,
                'groups': groups,
            },
        },
    })
