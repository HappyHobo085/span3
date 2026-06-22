import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'student.dart';
import 'personeel.dart';
import 'opsigter.dart';
import 'sekuriteitswag.dart';
import 'admin.dart';

export 'moon_api.dart';

void main() {
  runApp(const MyApp());
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

  @override
  void dispose() {
    _usernameController.dispose();
    super.dispose();
  }

  // All routing logic unchanged.
  void _handleLogin() {
    final input = _usernameController.text.trim();
    final lower = input.toLowerCase();
    Widget nextPage;

    switch (input) {
      case '0':
        nextPage = const HomePage();
        break;
      case '1':
        nextPage = const PersoneelHomePage();
        break;
      case '2':
        nextPage = const OpsigterHomePage();
        break;
      case '3':
        nextPage = const SekuriteitswagHomePage();
        break;
      default:
        if (lower == 'admin') {
          nextPage = const AdminHomePage();
          break;
        }
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
                'Ongeldige opsie. Voer 0, 1, 2, 3 in, of admin vir die admin-bladsy.'),
          ),
        );
        return;
    }

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => nextPage),
    );
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
                  // Hero logo card
                  GlassCard(
                    padding: const EdgeInsets.symmetric(
                        vertical: 28, horizontal: 24),
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
                  // Username field
                  GlassInput(
                    controller: _usernameController,
                    hintText: 'Gebruikersnaam',
                    keyboardType: TextInputType.text,
                  ),
                  const SizedBox(height: 12),
                  // Password field (display only — auth is handled by _handleLogin)
                  GlassInput(
                    hintText: 'Wagwoord',
                    obscureText: true,
                    prefixIcon:
                        const Icon(Icons.lock_outline, color: kTextMuted, size: 18),
                  ),
                  const SizedBox(height: 24),
                  // Login button
                  GradientActionButton(
                    label: 'Teken In',
                    onTap: _handleLogin,
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
