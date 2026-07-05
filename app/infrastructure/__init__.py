"""Infrastructure layer: concrete adapters implementing domain ports.

Depends on the domain layer. Never imported by domain or application. Wired
into use cases at the composition root (app.api.dependencies).
"""
