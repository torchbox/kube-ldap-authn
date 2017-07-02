#! /usr/bin/env python3
#
# Copyright (c) 2017 Torchbox Ltd.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely. This software is provided 'as-is', without any express or implied
# warranty.

from flask import Flask, request, jsonify, Response
import ldap, ldap.filter, logging, sys

logger = logging.getLogger('kube-ldap-authn')
logger.setLevel(logging.INFO)
hdl = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s [%(levelname)-8s] %(name)-15s: %(message)s')
hdl.setFormatter(formatter)
logger.addHandler(hdl)

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

@app.route('/authn', methods=['POST'])
def authn():
    auth_error = jsonify({
        'apiVersion': 'authentication.k8s.io/v1beta1',
        'kind': 'TokenReview',
        'status': {
            'authenticated': False,
        },
    })

    req = request.json
    if req is None:
        logger.info("invalid or missing request json")
        return auth_error

    if 'apiVersion' not in req or req['apiVersion'] != 'authentication.k8s.io/v1beta1':
        logger.info("invalid or missing apiVersion")
        return auth_error
    if 'kind' not in req or req['kind'] != 'TokenReview':
        logger.info("invalid or missing kind")
        return auth_error
    if 'spec' not in req or 'token' not in req['spec']:
        logger.info("invalid or missing spec")
        return auth_error

    token = req['spec']['token']

    try:
        ld = ldap.initialize(app.config['LDAP_URL'])
    except ldap.LDAPError as e:
        logger.info("LDAP connection error: " + str(e))
        return auth_error

    ld.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

    if app.config.get('LDAP_START_TLS', True) == True:
        try:
            ld.start_tls_s()
        except ldap.LDAPError as e:
            logger.info("LDAP TLS error: " + str(e))
            return auth_error

    try:
        ld.simple_bind_s(app.config['LDAP_BIND_DN'],
                         app.config['LDAP_BIND_PASSWORD'])
    except ldap.LDAPError as e:
        logger.info("LDAP bind error: " + str(e))
        return auth_error

    user_search = app.config['LDAP_USER_SEARCH_FILTER'].format(
                    token=ldap.filter.escape_filter_chars(token))

    try:
        r = ld.search_s(app.config['LDAP_USER_SEARCH_BASE'],
                        ldap.SCOPE_SUBTREE,
                        user_search,
                        [ app.config['LDAP_USER_NAME_ATTRIBUTE'],
                          app.config['LDAP_USER_UID_ATTRIBUTE'] ])
    except ldap.LDAPError as e:
        logger.info("LDAP search error: " + str(e))
        return auth_error

    if len(r) != 1:
        logger.info("expected 1 user, found " + str(len(r)))
        return auth_error

    username = r[0][1][app.config['LDAP_USER_NAME_ATTRIBUTE']][0].decode('ascii')
    uid = r[0][1][app.config['LDAP_USER_UID_ATTRIBUTE']][0].decode('ascii')

    group_search = app.config['LDAP_GROUP_SEARCH_FILTER'].format(
                        username=ldap.filter.escape_filter_chars(username),
                        dn=ldap.filter.escape_filter_chars(r[0][0]))
    try:
        g = ld.search_s(app.config['LDAP_GROUP_SEARCH_BASE'],
                        ldap.SCOPE_SUBTREE, group_search,
                        [ app.config['LDAP_GROUP_NAME_ATTRIBUTE'] ])
    except ldap.LDAPError as e:
        logger.info("LDAP search error: " + str(e))
        return auth_error

    groups = [
            i[1][app.config['LDAP_GROUP_NAME_ATTRIBUTE']][0].decode('ascii')
        for i in g ]

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
