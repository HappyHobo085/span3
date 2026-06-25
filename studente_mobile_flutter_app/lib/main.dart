import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_shared.dart';
import 'student.dart';
import 'personeel.dart';
import 'opsigter.dart';
import 'sekuriteitswag.dart';
import 'admin.dart';
import 'moon_api.dart';

void main() {
  runApp(const MyApp());
}

Map<String, dynamic> _decodeJwtPayload(String token) {
  final parts = token.split('.');
  if (parts.length != 3) {
    throw Exception('Ongeldige token');
  }

  final payload = base64Url.normalize(parts[1]);
  final decoded = utf8.decode(base64Url.decode(payload));
  return jsonDecode(decoded) as Map<String, dynamic>;
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MOON — Kampus Bestuur',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: kBg,
        colorScheme: ColorScheme.dark(
          primary: kAccent,
          secondary: kAccent2,
          surface: kSurface1,
        ),
        textTheme: GoogleFonts.interTextTheme(
          ThemeData.dark().textTheme,
        ),
      ),
      home: const LoginPage(),
    );
  }
}

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  bool _isLoading = false;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    final username = _usernameController.text.trim();
    final password = _passwordController.text.trim();

    if (username.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Colors.red,
          content: Text(
            'Voer asseblief gebruikersnaam en wagwoord in.',
            style: TextStyle(color: Colors.white),
          ),
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final loginData = await MoonApi.login(
        email: username,
        password: password,
      );

      final token = loginData['access_token'] as String;
      final payload = _decodeJwtPayload(token);
      final rolNaam = payload['rol_naam']?.toString() ?? '';

      Widget nextPage;

      switch (rolNaam) {
        case 'Administrateur':
          nextPage = const AdminHomePage();
          break;
        case 'Personeel':
          nextPage = const PersoneelHomePage();
          break;
        case 'Kampus_Opsigter':
          nextPage = const OpsigterHomePage();
          break;
        case 'Sekuriteit_Wag':
          nextPage = const SekuriteitswagHomePage();
          break;
        case 'Student':
          nextPage = const HomePage();
          break;
        default:
          throw Exception('Onbekende rol: $rolNaam');
      }

      if (!mounted) return;

        await MoonApi.getMyProfile();

        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => nextPage),
        );
    } catch (e) {
      debugPrint('LOGIN ERROR: $e');

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(
            'Login fout: $e',
            style: const TextStyle(color: Colors.white),
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 360),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  GlassCard(
                    padding: const EdgeInsets.symmetric(
                      vertical: 28,
                      horizontal: 24,
                    ),
                    child: Column(
                      children: [
                        ShaderMask(
                          shaderCallback: (bounds) =>
                              kGradient.createShader(bounds),
                          child: Text(
                            'MOON',
                            style: GoogleFonts.inter(
                              color: Colors.white,
                              fontSize: 28,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 4,
                            ),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'KAMPUS BESTUUR STELSEL',
                          style: GoogleFonts.inter(
                            color: kTextMuted,
                            fontSize: 9,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 2,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                  GlassInput(
                    controller: _usernameController,
                    hintText: 'Gebruikersnaam / Studentenommer',
                    keyboardType: TextInputType.text,
                  ),
                  const SizedBox(height: 12),
                  GlassInput(
                    controller: _passwordController,
                    hintText: 'Wagwoord',
                    obscureText: true,
                    prefixIcon: const Icon(
                      Icons.lock_outline,
                      color: kTextMuted,
                      size: 18,
                    ),
                  ),
                  const SizedBox(height: 24),
                  GradientActionButton(
                    label: _isLoading ? 'Teken in...' : 'Teken In',
                    onTap: _isLoading
                        ? () {}
                        : () async {
                            await _handleLogin();
                          },
                    width: double.infinity,
                    height: 48,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}