from django.core.management.base import BaseCommand
from django.utils import timezone
from foodapp.models import User, Restaurant, RestaurantAccount, Order, OrderItem
import subprocess
import os
import json
import tempfile

class Command(BaseCommand):
    help = 'Integrates C++ code with Django models for demonstration purposes'

    def add_arguments(self, parser):
        parser.add_argument('--action', type=str, choices=['account', 'restaurant', 'order'], 
                           help='Type of C++ integration to run')

    def handle(self, *args, **options):
        action = options.get('action')
        if not action:
            self.stdout.write(self.style.WARNING('Please specify an action: --action=account|restaurant|order'))
            return

        # Get the directory where the C++ files are located
        cpp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c++')
        
        if action == 'account':
            self.run_account_integration(cpp_dir)
        elif action == 'restaurant':
            self.run_restaurant_integration(cpp_dir)
        elif action == 'order':
            self.run_order_integration(cpp_dir)

    def run_account_integration(self, cpp_dir):
        self.stdout.write(self.style.SUCCESS('Running Account C++ integration'))
        
        # Get sample user data
        users = User.objects.filter(is_staff=False)[:5]
        if not users:
            self.stdout.write(self.style.WARNING('No users found in the database'))
            return
            
        # Create a temporary file to store user data
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_file:
            user_data = [{
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined.isoformat()
            } for user in users]
            json.dump(user_data, temp_file)
            temp_file_path = temp_file.name
        
        # Compile and run the C++ code
        try:
            # Compile the C++ code
            cpp_file = os.path.join(cpp_dir, 'Account_creation_process.cpp')
            output_file = os.path.join(cpp_dir, 'account_process.exe')
            
            # Check if the C++ file exists
            if not os.path.exists(cpp_file):
                self.stdout.write(self.style.ERROR(f'C++ file not found: {cpp_file}'))
                return
                
            # Compile the C++ code
            compile_cmd = f'g++ -std=c++17 "{cpp_file}" -o "{output_file}"'
            self.stdout.write(f'Compiling: {compile_cmd}')
            compile_process = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True)
            
            if compile_process.returncode != 0:
                self.stdout.write(self.style.ERROR(f'Compilation failed: {compile_process.stderr}'))
                return
                
            # Run the compiled C++ program
            run_cmd = f'"{output_file}" "{temp_file_path}"'
            self.stdout.write(f'Running: {run_cmd}')
            run_process = subprocess.run(run_cmd, shell=True, capture_output=True, text=True)
            
            if run_process.returncode != 0:
                self.stdout.write(self.style.ERROR(f'Execution failed: {run_process.stderr}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'C++ output: {run_process.stdout}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def run_restaurant_integration(self, cpp_dir):
        self.stdout.write(self.style.SUCCESS('Running Restaurant C++ integration'))
        
        # Get sample restaurant data
        restaurant_accounts = RestaurantAccount.objects.all()[:5]
        if not restaurant_accounts:
            self.stdout.write(self.style.WARNING('No restaurant accounts found in the database'))
            return
            
        # Create a temporary file to store restaurant data
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_file:
            restaurant_data = [{
                'id': ra.id,
                'restaurant_name': ra.restaurant.name,
                'owner_username': ra.user.username,
                'status': ra.status,
                'account_type': ra.account_type,
                'created_at': ra.created_at.isoformat(),
                'city': ra.restaurant.city.name,
                'address': ra.restaurant.address,
                'phone': ra.restaurant.phone,
                'email': ra.restaurant.email
            } for ra in restaurant_accounts]
            json.dump(restaurant_data, temp_file)
            temp_file_path = temp_file.name
        
        # Compile and run the C++ code
        try:
            # Compile the C++ code
            cpp_file = os.path.join(cpp_dir, 'Restaurant_account_creation_process.cpp')
            output_file = os.path.join(cpp_dir, 'restaurant_process.exe')
            
            # Check if the C++ file exists
            if not os.path.exists(cpp_file):
                self.stdout.write(self.style.ERROR(f'C++ file not found: {cpp_file}'))
                return
                
            # Compile the C++ code
            compile_cmd = f'g++ -std=c++17 "{cpp_file}" -o "{output_file}"'
            self.stdout.write(f'Compiling: {compile_cmd}')
            compile_process = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True)
            
            if compile_process.returncode != 0:
                self.stdout.write(self.style.ERROR(f'Compilation failed: {compile_process.stderr}'))
                return
                
            # Run the compiled C++ program
            run_cmd = f'"{output_file}" "{temp_file_path}"'
            self.stdout.write(f'Running: {run_cmd}')
            run_process = subprocess.run(run_cmd, shell=True, capture_output=True, text=True)
            
            if run_process.returncode != 0:
                self.stdout.write(self.style.ERROR(f'Execution failed: {run_process.stderr}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'C++ output: {run_process.stdout}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def run_order_integration(self, cpp_dir):
        self.stdout.write(self.style.SUCCESS('Running Order C++ integration'))
        
        # Get sample order data
        orders = Order.objects.all()[:5]
        if not orders:
            self.stdout.write(self.style.WARNING('No orders found in the database'))
            return
            
        # Create a temporary file to store order data
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_file:
            order_data = [{
                'order_id': order.id,
                'restaurant_name': order.restaurant.name,
                'user_id': order.user.id if order.user else None,
                'user_name': order.user.username if order.user else order.customer_name,
                'status': order.status,
                'total_amount': float(order.total_amount),
                'payment_method': order.payment_method,
                'order_time': order.order_time.isoformat(),
                'delivery_time': order.delivery_time.isoformat() if order.delivery_time else None,
                'items': [{
                    'dish_name': item.dish.name,
                    'quantity': item.quantity,
                    'price': float(item.price)
                } for item in order.items.all()]
            } for order in orders]
            json.dump(order_data, temp_file)
            temp_file_path = temp_file.name
        
        # Compile and run the C++ code
        try:
            # Compile the C++ code
            cpp_file = os.path.join(cpp_dir, 'Order_Process.cpp')
            output_file = os.path.join(cpp_dir, 'order_process.exe')
            
            # Check if the C++ file exists
            if not os.path.exists(cpp_file):
                self.stdout.write(self.style.ERROR(f'C++ file not found: {cpp_file}'))
                return
                
            # Compile the C++ code
            compile_cmd = f'g++ -std=c++17 "{cpp_file}" -o "{output_file}"'
            self.stdout.write(f'Compiling: {compile_cmd}')
            compile_process = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True)
            
            if compile_process.returncode != 0:
                self.stdout.write(self.style.ERROR(f'Compilation failed: {compile_process.stderr}'))
                return
                
            # Run the compiled C++ program
            run_cmd = f'"{output_file}" "{temp_file_path}"'
            self.stdout.write(f'Running: {run_cmd}')
            run_process = subprocess.run(run_cmd, shell=True, capture_output=True, text=True)
            
            if run_process.returncode != 0:
                self.stdout.write(self.style.ERROR(f'Execution failed: {run_process.stderr}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'C++ output: {run_process.stdout}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)