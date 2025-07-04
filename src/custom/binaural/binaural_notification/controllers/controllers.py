# -*- coding: utf-8 -*-
# from odoo import http


# class BinauralNotification(http.Controller):
#     @http.route('/binaural_notification/binaural_notification', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/binaural_notification/binaural_notification/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('binaural_notification.listing', {
#             'root': '/binaural_notification/binaural_notification',
#             'objects': http.request.env['binaural_notification.binaural_notification'].search([]),
#         })

#     @http.route('/binaural_notification/binaural_notification/objects/<model("binaural_notification.binaural_notification"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('binaural_notification.object', {
#             'object': obj
#         })

