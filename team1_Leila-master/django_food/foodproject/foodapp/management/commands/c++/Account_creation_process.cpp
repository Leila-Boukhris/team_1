#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <nlohmann/json.hpp>

// If nlohmann/json.hpp is not available, use this simplified version
#ifndef NLOHMANN_JSON_VERSION_MAJOR
#include <map>
#include <sstream>

namespace nlohmann {
    class json {
    private:
        std::map<std::string, std::string> data;
    public:
        static json parse(const std::string& str) {
            json j;
            // Simple parsing logic (this is just a placeholder)
            return j;
        }
        
        std::string dump(int indent = -1) const {
            std::ostringstream oss;
            oss << "{";
            // Simple serialization logic
            oss << "}";
            return oss.str();
        }
        
        std::string operator[](const std::string& key) const {
            auto it = data.find(key);
            if (it != data.end()) {
                return it->second;
            }
            return "";
        }
    };
}
#endif

using namespace std;

namespace Account {
    class Account {
    private:
        int user_id;
        string username;
        string email;
        string first_name;
        string last_name;
        string date_joined;
    public:
        Account() {}
        Account(int user_id, string username, string email, string first_name, string last_name, string date_joined) {
            this->user_id = user_id;
            this->username = username;
            this->email = email;
            this->first_name = first_name;
            this->last_name = last_name;
            this->date_joined = date_joined;
        }
        
        // Getters
        int get_user_id() const { return user_id; }
        string get_username() const { return username; }
        string get_email() const { return email; }
        string get_first_name() const { return first_name; }
        string get_last_name() const { return last_name; }
        string get_date_joined() const { return date_joined; }
        
        // Setters
        void set_username(const string& username) { this->username = username; }
        void set_email(const string& email) { this->email = email; }
        void set_first_name(const string& first_name) { this->first_name = first_name; }
        void set_last_name(const string& last_name) { this->last_name = last_name; }
        
        // Utility methods
        string get_full_name() const {
            if (first_name.empty() && last_name.empty()) {
                return username;
            }
            return first_name + " " + last_name;
        }
        
        string to_string() const {
            return "User ID: " + std::to_string(user_id) +
                "\nUsername: " + username +
                "\nEmail: " + email +
                "\nName: " + get_full_name() +
                "\nJoined: " + date_joined;
        }
        
        // Convert to JSON
        nlohmann::json to_json() const {
            nlohmann::json j;
            j["user_id"] = user_id;
            j["username"] = username;
            j["email"] = email;
            j["first_name"] = first_name;
            j["last_name"] = last_name;
            j["full_name"] = get_full_name();
            j["date_joined"] = date_joined;
            return j;
        }
        
        // Create from JSON
        static Account from_json(const nlohmann::json& j) {
            return Account(
                j.contains("user_id") ? j["user_id"].get<int>() : 0,
                j.contains("username") ? j["username"].get<string>() : "",
                j.contains("email") ? j["email"].get<string>() : "",
                j.contains("first_name") ? j["first_name"].get<string>() : "",
                j.contains("last_name") ? j["last_name"].get<string>() : "",
                j.contains("date_joined") ? j["date_joined"].get<string>() : ""
            );
        }
    };
}

int main(int argc, char* argv[]) {
    try {
        // Check if a file path was provided
        if (argc < 2) {
            std::cerr << "Usage: " << argv[0] << " <json_file_path>" << std::endl;
            return 1;
        }
        
        // Read the JSON file
        std::string file_path = argv[1];
        std::ifstream file(file_path);
        if (!file.is_open()) {
            std::cerr << "Failed to open file: " << file_path << std::endl;
            return 1;
        }
        
        // Parse the JSON data
        nlohmann::json json_data;
        file >> json_data;
        file.close();
        
        // Process the accounts
        std::vector<Account::Account> accounts;
        for (const auto& user_json : json_data) {
            Account::Account account = Account::Account::from_json(user_json);
            accounts.push_back(account);
        }
        
        // Output the processed accounts
        std::cout << "Processed " << accounts.size() << " accounts:" << std::endl;
        for (const auto& account : accounts) {
            std::cout << "\n-----------------------------------" << std::endl;
            std::cout << account.to_string() << std::endl;
        }
        
        // Create a JSON response
        nlohmann::json response;
        response["status"] = "success";
        response["message"] = "Successfully processed " + std::to_string(accounts.size()) + " accounts";
        response["accounts"] = nlohmann::json::array();
        
        for (const auto& account : accounts) {
            response["accounts"].push_back(account.to_json());
        }
        
        // Output the JSON response
        std::cout << "\n-----------------------------------" << std::endl;
        std::cout << "JSON Response:" << std::endl;
        std::cout << response.dump(4) << std::endl;
        
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}


