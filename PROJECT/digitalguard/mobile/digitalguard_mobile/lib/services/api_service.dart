import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = 'http://10.0.2.2:8000'; // Default Android Emulator host IP
  static String? _authToken;

  static void setAuthToken(String token) {
    _authToken = token;
  }

  static Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/login/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': password}),
      ).timeout(const Duration(seconds: 4));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _authToken = data['data']?['tokens']?['access'];
        return {'success': true, 'data': data['data']};
      }
    } catch (_) {
      // Fall back to demo mode if backend is unreachable
    }

    // Demo Mode fallback
    return {
      'success': true,
      'data': {
        'user': {'display_name': 'Sarah Connor', 'email': email},
        'tokens': {'access': 'demo_mobile_token'}
      }
    };
  }

  static Future<Map<String, dynamic>> getDashboardSummary() async {
    return {
      'total_events': 142,
      'threats_detected': 3,
      'screen_time_mins': 165,
      'unread_alerts': 2,
    };
  }

  static Future<List<Map<String, dynamic>>> getChildren() async {
    return [
      {'id': '1', 'name': 'Alex', 'age': 12, 'avatar': '👦', 'status': 'Protected'},
      {'id': '2', 'name': 'Emma', 'age': 8, 'avatar': '👧', 'status': 'Protected'},
    ];
  }

  static Future<List<Map<String, dynamic>>> getAlerts() async {
    return [
      {
        'id': '1',
        'title': 'Phishing Intercepted',
        'message': 'Alex attempted to open a deceptive login page. Shield blocked connection.',
        'severity': 'CRITICAL',
        'time': '15m ago',
        'read': false
      },
      {
        'id': '2',
        'title': 'Toxic Language Filtered',
        'message': 'AI detected bullying patterns on Discord. Content blurred.',
        'severity': 'HIGH',
        'time': '1h ago',
        'read': false
      },
      {
        'id': '3',
        'title': 'Game Time Limit Warning',
        'message': 'Roblox daily allowance (60m) reached.',
        'severity': 'MEDIUM',
        'time': '3h ago',
        'read': true
      }
    ];
  }
}
