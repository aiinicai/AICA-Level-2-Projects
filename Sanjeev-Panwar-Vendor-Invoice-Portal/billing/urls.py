from django.urls import path
from django.contrib.auth import views as auth
from . import views
urlpatterns=[
 path('',views.home,name='home'),
 path('register/',views.register,name='register'),
 path('login/',auth.LoginView.as_view(template_name='billing/login.html'),name='login'),
 path('logout/',auth.LogoutView.as_view(),name='logout'),
 path('password-reset/',auth.PasswordResetView.as_view(template_name='billing/password_reset.html',email_template_name='billing/password_reset_email.txt',success_url='/password-reset/done/'),name='password_reset'),
 path('password-reset/done/',auth.PasswordResetDoneView.as_view(template_name='billing/simple_message.html',extra_context={'heading':'Password reset requested','detail':'If the email is registered, a test email has been written to local_demo/test_emails.'}),name='password_reset_done'),
 path('reset/<uidb64>/<token>/',auth.PasswordResetConfirmView.as_view(template_name='billing/password_confirm.html',success_url='/reset/done/'),name='password_reset_confirm'),
 path('reset/done/',auth.PasswordResetCompleteView.as_view(template_name='billing/simple_message.html',extra_context={'heading':'Password changed','detail':'You can now sign in.'}),name='password_reset_complete'),
 path('upload/',views.upload,name='upload'),
 path('invoice/<int:pk>/',views.invoice_detail,name='invoice_detail'),
 path('document/<int:pk>/',views.download_document,name='download_document'),
 path('finance/',views.finance_dashboard,name='finance'),
 path('finance/vendors/',views.finance_vendors,name='finance_vendors'),
 path('finance/vendors/<int:pk>/approve/',views.approve_vendor,name='approve_vendor'),
 path('finance/invoice/<int:pk>/',views.finance_review,name='finance_review'),
 path('finance/export/',views.export_csv,name='export_csv'),
]
