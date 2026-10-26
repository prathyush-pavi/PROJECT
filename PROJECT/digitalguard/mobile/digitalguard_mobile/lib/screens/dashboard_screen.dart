import 'package:flutter/material.dart';
import '../services/api_service.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _currentIndex = 0;
  Map<String, dynamic> _summary = {};
  List<Map<String, dynamic>> _alerts = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() async {
    final summary = await ApiService.getDashboardSummary();
    final alerts = await ApiService.getAlerts();
    setState(() {
      _summary = summary;
      _alerts = alerts;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F1322),
        elevation: 0,
        title: const Row(
          children: [
            Icon(Icons.shield_rounded, color: Color(0xFF818CF8)),
            SizedBox(width: 8),
            Text('DigitalGuard', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _loadData,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _buildTabBody(),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (idx) => setState(() => _currentIndex = idx),
        backgroundColor: const Color(0xFF0F1322),
        selectedItemColor: const Color(0xFF818CF8),
        unselectedItemColor: Colors.grey,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.dashboard_rounded), label: 'Overview'),
          BottomNavigationBarItem(icon: Icon(Icons.notifications_rounded), label: 'Alerts'),
          BottomNavigationBarItem(icon: Icon(Icons.policy_rounded), label: 'Policies'),
        ],
      ),
    );
  }

  Widget _buildTabBody() {
    if (_currentIndex == 0) return _buildOverviewTab();
    if (_currentIndex == 1) return _buildAlertsTab();
    return _buildPoliciesTab();
  }

  Widget _buildOverviewTab() {
    return ListView(
      padding: const EdgeInsets.all(16.0),
      children: [
        Row(
          children: [
            _buildStatCard('Screen Time', '2h 45m', Icons.timer_rounded, const Color(0xFF818CF8)),
            const SizedBox(width: 12),
            _buildStatCard('Threats Blocked', '${_summary['threats_detected'] ?? 0}', Icons.block_rounded, const Color(0xFFEF4444)),
          ],
        ),
        const SizedBox(height: 20),
        const Text(
          'Monitored Children',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        _buildChildCard('Alex Connor', '12 yrs', '👦', 'Windows Gaming PC', true),
        const SizedBox(height: 8),
        _buildChildCard('Emma Connor', '8 yrs', '👧', 'Family Tablet', true),
        const SizedBox(height: 20),
        const Text(
          'Recent Alerts',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        ..._alerts.take(2).map(_buildAlertTile),
      ],
    );
  }

  Widget _buildAlertsTab() {
    return ListView.separated(
      padding: const EdgeInsets.all(16.0),
      itemCount: _alerts.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (_, i) => _buildAlertTile(_alerts[i]),
    );
  }

  Widget _buildPoliciesTab() {
    return ListView(
      padding: const EdgeInsets.all(16.0),
      children: [
        const Text(
          'Website Filtering Rules',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        _buildPolicyTile('phishing-bank-login.xyz', 'BLOCK', Icons.block, Colors.red),
        _buildPolicyTile('reddit.com', 'WARN', Icons.warning_amber_rounded, Colors.orange),
        _buildPolicyTile('khanacademy.org', 'ALLOW', Icons.check_circle_rounded, Colors.green),
        const SizedBox(height: 24),
        const Text(
          'Application Limits (Windows)',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        _buildPolicyTile('cheatengine.exe', 'BLOCKED', Icons.dangerous_rounded, Colors.red),
        _buildPolicyTile('roblox.exe', '60m Daily Quota', Icons.hourglass_bottom_rounded, Colors.amber),
      ],
    );
  }

  Widget _buildStatCard(String title, String val, IconData icon, Color col) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF14192B),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withOpacity(0.06)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: col, size: 28),
            const SizedBox(height: 12),
            Text(val, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text(title, style: const TextStyle(fontSize: 12, color: Colors.grey)),
          ],
        ),
      ),
    );
  }

  Widget _buildChildCard(String name, String age, String avatar, String device, bool active) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF14192B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Row(
        children: [
          Text(avatar, style: const TextStyle(fontSize: 32)),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                Text('$age • $device', style: const TextStyle(color: Colors.grey, fontSize: 12)),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.green.withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Text('Protected', style: TextStyle(color: Colors.green, fontSize: 11, fontWeight: FontWeight.bold)),
          )
        ],
      ),
    );
  }

  Widget _buildAlertTile(Map<String, dynamic> al) {
    final isCrit = al['severity'] == 'CRITICAL';
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF14192B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: isCrit ? Colors.red.withOpacity(0.4) : Colors.white.withOpacity(0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(al['title'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
              Text(al['time'] ?? '', style: const TextStyle(color: Colors.grey, fontSize: 11)),
            ],
          ),
          const SizedBox(height: 6),
          Text(al['message'] ?? '', style: const TextStyle(color: Colors.grey, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildPolicyTile(String title, String badge, IconData icon, Color col) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF14192B),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Icon(icon, color: col, size: 20),
          const SizedBox(width: 12),
          Expanded(child: Text(title, style: const TextStyle(fontSize: 13))),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(color: col.withOpacity(0.15), borderRadius: BorderRadius.circular(6)),
            child: Text(badge, style: TextStyle(color: col, fontSize: 11, fontWeight: FontWeight.bold)),
          )
        ],
      ),
    );
  }
}
