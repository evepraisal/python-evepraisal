from . import app, views


# Login stuff
app.route('/login', methods=['GET', 'POST'])(views.login)
app.route('/logout')(views.logout)

# Main site stuff
app.route('/', methods=['GET', 'POST'])(views.index)
app.route('/history')(views.history)
app.route('/options', methods=['GET', 'POST'])(views.options)
app.route('/estimate', methods=['POST'])(views.estimate_cost)
app.route('/e/<int:result_id>', methods=['GET'])(views.display_result)
app.route('/estimate/<int:result_id>', methods=['GET'])(views.display_result)
app.route('/latest')(views.latest)
app.route('/legal')(views.legal)

# Static Stuff (should really be served from a legit file server)
app.route('/robots.txt')(views.static_from_root)
app.route('/favicon.ico')(views.static_from_root)
