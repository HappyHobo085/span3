// Flutter material widgets package.
import 'package:flutter/material.dart';
import 'app_shared.dart';
import 'student.dart';
import 'personeel.dart';
import 'opsigter.dart';
import 'sekuriteitswag.dart';

/// Backend API (FastAPI `main.py`) — sien [moon_api.dart].
export 'moon_api.dart';

// App entry point.
void main() {
  // Backend: stel URL vir jou omgewing (Android-emulator: 10.0.2.2; iOS-simulator/Desktop: 127.0.0.1).
  // MoonApi.baseUrl = 'http://127.0.0.1:8000';
  // Na werklike login teen POST /token: MoonApi.bearerToken = access_token;
  runApp(const MyApp());
}

// Root app widget.
class MyApp extends StatelessWidget {
  // Constructor.
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Main app setup.
    return MaterialApp(
      // App title.
      title: 'Studenten - Docenten',
      // Global app theme.
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.white),
      ),
      // First page users see.
      home: const LoginPage(),
    );
  }
}

// Login screen widget.
class LoginPage extends StatefulWidget {
  // Constructor.
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  // Controller to read the input value from the text field.
  final TextEditingController _usernameController = TextEditingController();

  @override
  void dispose() {
    _usernameController.dispose();
    super.dispose();
  }

  // Handle the logic when user presses the login button.
  void _handleLogin() {
    String input = _usernameController.text.trim();
    Widget nextPage;

    switch (input) {
      case '0':
        // Navigate to student
        nextPage = const HomePage();
        break;
      case '1':
        // Navigate to personeel
        nextPage = const PersoneelHomePage();
        break;
      case '2':
        // Navigate to opsigter
        nextPage = const OpsigterHomePage();
        break;
      case '3':
        // Navigate to sekuriteitswag
        nextPage = const SekuriteitswagHomePage();
        break;
      default:
        // Show an error if they enter anything else.
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content:
                  Text('Ongeldige opsie. Voer asseblief 0, 1, 2, of 3 in.')),
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
    // Basic page structure.
    return Scaffold(
        // Screen background color.
        backgroundColor: loginPageBackground,
        body: SafeArea(
          child: SingleChildScrollView(
            child: Center(
              // Vertical layout for image, fields and button.
              child: Column(
                mainAxisSize: MainAxisSize.max,
                children: [
                  // Top image container.
                  Container(
                    width: 395.1,
                    height: 285.38,
                    decoration: const BoxDecoration(
                      color: Color(0xFF0A0F1F),
                    ),
                    child: ClipRRect(
                      // Rounded image corners.
                      borderRadius: BorderRadius.circular(8),
                      child: Image.asset(
                        // Login page image.
                        'assets/ChatGPT_Image_Mar_26_2026_04_16_53_PM.png',
                        width: 200,
                        height: 60.43,
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsetsDirectional.fromSTEB(0, 50, 0, 0),
                    child: Row(
                      mainAxisSize: MainAxisSize.max,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Align(
                          alignment: const AlignmentDirectional(0, 0),
                          child: _LoginFieldContainer(
                            // Email text field.
                            child: TextField(
                              controller: _usernameController,
                              keyboardType: TextInputType.number,
                              style: const TextStyle(color: Colors.white),
                              decoration: _loginInputDecoration(
                                context,
                                hintText: 'gebruikers inligting',
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsetsDirectional.fromSTEB(0, 10, 0, 0),
                    child: Row(
                      mainAxisSize: MainAxisSize.max,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Align(
                          alignment: const AlignmentDirectional(0, 0),
                          child: _LoginFieldContainer(
                            // Password text field.
                            child: TextField(
                              // Hide password characters.
                              obscureText: true,
                              style: const TextStyle(color: Colors.white),
                              decoration: _loginInputDecoration(
                                context,
                                hintText: 'wagwoord',
                                // Lock icon inside field.
                                prefixIcon:
                                    const Icon(Icons.lock, color: Colors.white),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsetsDirectional.fromSTEB(0, 80, 0, 0),
                    child: SingleChildScrollView(
                      // Keep layout safe on small widths.
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        mainAxisSize: MainAxisSize.max,
                        children: [
                          // Login action button.
                          _LoginGradientButton(onLogin: _handleLogin),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ));
  }
}

// Shared container style for login input boxes.
class _LoginFieldContainer extends StatelessWidget {
  // Child widget inside the styled box.
  final Widget child;

  // Constructor.
  const _LoginFieldContainer({required this.child});

  @override
  Widget build(BuildContext context) {
    // Neon outlined input wrapper.
    return Container(
      width: 350,
      height: 50,
      decoration: BoxDecoration(
        color: loginPageBackground,
        boxShadow: const [
          BoxShadow(
            blurRadius: 10,
            color: Color(0x4D7B61FF),
            offset: Offset(0, 2),
          )
        ],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: const Color(0xFF7B61FF),
          width: 1.5,
        ),
      ),
      // Inner container that holds the field.
      child: SizedBox(
        width: 200,
        child: child,
      ),
    );
  }
}

// Builds a reusable input decoration for login fields.
InputDecoration _loginInputDecoration(
  BuildContext context, {
  required String hintText,
  Widget? prefixIcon,
}) {
  // Return style settings for text fields.
  return InputDecoration(
    isDense: true,
    hintText: hintText,
    hintStyle: const TextStyle(color: Colors.white),
    filled: true,
    fillColor: loginPageBackground,
    enabledBorder: OutlineInputBorder(
      borderSide: const BorderSide(color: Color(0x00000000), width: 1),
      borderRadius: BorderRadius.circular(8),
    ),
    focusedBorder: OutlineInputBorder(
      borderSide: const BorderSide(color: Color(0x00000000), width: 1),
      borderRadius: BorderRadius.circular(8),
    ),
    errorBorder: OutlineInputBorder(
      borderSide: BorderSide(
        color: Theme.of(context).colorScheme.error,
        width: 1,
      ),
      borderRadius: BorderRadius.circular(8),
    ),
    focusedErrorBorder: OutlineInputBorder(
      borderSide: BorderSide(
        color: Theme.of(context).colorScheme.error,
        width: 1,
      ),
      borderRadius: BorderRadius.circular(8),
    ),
    prefixIcon: prefixIcon,
  );
}

// Login button wrapper widget.
class _LoginGradientButton extends StatelessWidget {
  final VoidCallback onLogin;

  // Constructor.
  const _LoginGradientButton({required this.onLogin});

  @override
  Widget build(BuildContext context) {
    // Reuse common gradient button widget.
    return GradientActionButton(
      label: 'Teken in',
      onTap: onLogin,
    );
  }
}

