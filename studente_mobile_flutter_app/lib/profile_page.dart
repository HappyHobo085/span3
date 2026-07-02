import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'moon_api.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  bool _loading = true;
  Map<String, dynamic>? _profile;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final data = await MoonApi.getMyProfile();

      if (!mounted) return;

      setState(() {
        _profile = data;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  String _displayNumber(Map<String, dynamic> p) {
    return p['student_nommer']?.toString() ??
        p['personeel_nommer']?.toString() ??
        p['opsigter_nommer']?.toString() ??
        p['wag_nommer']?.toString() ??
        'Nie beskikbaar';
  }

  String _numberLabel(Map<String, dynamic> p) {
    final rol = p['rol']?.toString() ?? '';

    if (rol == 'Student') return 'Studentnommer';
    if (rol == 'Personeel') return 'Personeelnommer';
    if (rol == 'Kampus_Opsigter') return 'Opsigternommer';
    if (rol == 'Sekuriteit_Wag') return 'Wagnommer';

    return 'Nommer';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(
              title: 'Profiel',
              subtitle: 'My besonderhede',
            ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Text(
                            _error!,
                            style: GoogleFonts.inter(color: Colors.red),
                          ),
                        )
                      : _buildProfile(_profile!),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProfile(Map<String, dynamic> p) {
    final naam = p['naam']?.toString() ?? '';
    final van = p['van']?.toString() ?? '';
    final rol = p['rol']?.toString() ?? '';
    final fotoUrl = p['foto_url']?.toString() ?? '';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          GlassCard(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                if (fotoUrl.isNotEmpty)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(60),
                    child: Image.network(
                      '${MoonApi.baseUrl}$fotoUrl',
                      width: 110,
                      height: 110,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const Icon(
                        Icons.person,
                        color: kTextMuted,
                        size: 90,
                      ),
                    ),
                  )
                else
                  const Icon(
                    Icons.person,
                    color: kTextMuted,
                    size: 95,
                  ),

                const SizedBox(height: 14),

                Text(
                  '$naam $van',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                  ),
                ),

                const SizedBox(height: 4),

                Text(
                  rol,
                  style: GoogleFonts.inter(
                    color: kAccent,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          GlassCard(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                _InfoRow(label: _numberLabel(p), value: _displayNumber(p)),
                const _ThinDivider(),
                _InfoRow(label: 'E-pos', value: p['epos']?.toString() ?? ''),
                const _ThinDivider(),
                _InfoRow(label: 'Selfoon', value: p['selfoon']?.toString() ?? ''),
                const _ThinDivider(),
                _InfoRow(label: 'Status', value: p['status']?.toString() ?? ''),
                const _ThinDivider(),
                _InfoRow(
                  label: 'Kampus',
                  value: p['kampus']?.toString() ?? 'Nie gekoppel nie',
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          GradientActionButton(
            label: 'Verander Foto',
            onTap: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Foto upload kom volgende')),
              );
            },
            height: 48,
          ),

          const SizedBox(height: 12),

          OutlineActionButton(
            label: 'Logout',
            onTap: () {
              MoonApi.bearerToken = null;
              MoonApi.myProfile = null;
              Navigator.popUntil(context, (route) => route.isFirst);
            },
            height: 48,
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: GoogleFonts.inter(
                color: kTextMuted,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value.isEmpty ? 'Nie beskikbaar' : value,
              textAlign: TextAlign.right,
              style: GoogleFonts.inter(
                color: kText1,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ThinDivider extends StatelessWidget {
  const _ThinDivider();

  @override
  Widget build(BuildContext context) {
    return const Divider(
      color: Color(0x0AFFFFFF),
      height: 1,
    );
  }
}