// Flutter material widgets package.
import 'package:flutter/material.dart';

// Main brown color used in the app theme.
const Color loginBrown = Color(0xFF935E28);
// Dark blue helper color used in the app theme.
const Color loginDarkBlue = Color(0xFF0E1E3B);
// Main page background color used on all screens.
const Color loginPageBackground = Color(0xFF0D132C);

// App entry point.
void main() {
  // Start the Flutter app.
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
class LoginPage extends StatelessWidget {
  // Constructor.
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    // Basic page structure.
    return Scaffold(
      // Screen background color.
      backgroundColor: loginPageBackground,
      body: SafeArea(
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
                  child: Image.network(
                    // Login page image.
                    'https://cdn.discordapp.com/attachments/1474016815481880700/1486730725779570808/ChatGPT_Image_Mar_26_2026_04_16_53_PM.png?ex=69c69163&is=69c53fe3&hm=1c0736abbd6631bd072516a005e2dd570829acd58d60ea12c9b30898fb7de612&',
                    width: 200,
                    height: 60.43,
                    fit: BoxFit.cover,
                  ),
                ),
              ),
              Padding(
                padding: EdgeInsetsDirectional.fromSTEB(0, 50, 0, 0),
                child: Row(
                  mainAxisSize: MainAxisSize.max,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Align(
                      alignment: AlignmentDirectional(0, 0),
                      child: _LoginFieldContainer(
                        // Email text field.
                        child: TextField(
                          keyboardType: TextInputType.emailAddress,
                          style: const TextStyle(color: Colors.white),
                          decoration: _loginInputDecoration(
                            context,
                            hintText: 'studentenommer',
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: EdgeInsetsDirectional.fromSTEB(0, 10, 0, 0),
                child: Row(
                  mainAxisSize: MainAxisSize.max,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Align(
                      alignment: AlignmentDirectional(0, 0),
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
                            prefixIcon: const Icon(Icons.lock, color: Colors.white),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: EdgeInsetsDirectional.fromSTEB(0, 80, 0, 0),
                child: SingleChildScrollView(
                  // Keep layout safe on small widths.
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    mainAxisSize: MainAxisSize.max,
                    children: [
                      // Login action button.
                      _LoginGradientButton(),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
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
      child: Container(
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
  // Constructor.
  const _LoginGradientButton();

  @override
  Widget build(BuildContext context) {
    // Reuse common gradient button widget.
    return _GradientActionButton(
      label: 'Teken in',
      onTap: () {
        // Go to home page after pressing login.
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => const HomePage()),
        );
      },
    );
  }
}

// Reusable neon gradient action button.
class _GradientActionButton extends StatelessWidget {
  // Button text.
  final String label;
  // Action when button is tapped.
  final VoidCallback onTap;
  // Button width.
  final double width;
  // Button height.
  final double height;

  // Constructor with optional size values.
  const _GradientActionButton({
    required this.label,
    required this.onTap,
    this.width = 324.65,
    this.height = 45,
  });

  @override
  Widget build(BuildContext context) {
    // Tap area with custom visual style.
    return InkWell(
      splashColor: Colors.transparent,
      focusColor: Colors.transparent,
      hoverColor: Colors.transparent,
      highlightColor: Colors.transparent,
      onTap: onTap,
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          // Glow effect around button.
          boxShadow: const [
            BoxShadow(
              blurRadius: 25,
              color: Color(0xA87B61FF),
              offset: Offset(0, 2),
              spreadRadius: 2,
            ),
          ],
          // Vertical neon gradient fill.
          gradient: const LinearGradient(
            colors: [Color(0xFF7B61FF), Color(0xFF00C2FF)],
            stops: [0, 1],
            begin: AlignmentDirectional(0, -1),
            end: AlignmentDirectional(0, 1),
          ),
          borderRadius: BorderRadius.circular(15),
          border: Border.all(color: const Color(0xFF7B61FF)),
        ),
        alignment: AlignmentDirectional(0, 0),
        child: Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}

// Home screen with two main panels.
class HomePage extends StatelessWidget {
  // Constructor.
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: loginPageBackground,
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: SizedBox(
              height: 240,
              width: double.infinity,
              child: Row(
                children: [
                  // Panel that opens access scanning page.
                  Expanded(
                    child: _OutlinedPanel(
                      text: 'Toegang skandering',
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const LeftEmptyPage(),
                          ),
                        );
                      },
                    ),
                  ),
                  // Space between the two panels.
                  const SizedBox(width: 16),
                  // Panel that opens class scanning page.
                  Expanded(
                    child: _OutlinedPanel(
                      text: 'Klas skandering',
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const RightEmptyPage(),
                          ),
                        );
                      },
                    ),
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

// Reusable clickable panel used on home screen.
class _OutlinedPanel extends StatelessWidget {
  // Panel title text.
  final String text;
  // Tap action.
  final VoidCallback onTap;

  // Constructor.
  const _OutlinedPanel({
    required this.text,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    // Detect taps anywhere on the panel.
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          // Match screen background.
          color: loginPageBackground,
          // Neon border line.
          border: const Border.fromBorderSide(
            BorderSide(color: Color(0xFF7B61FF), width: 1.5),
          ),
          // Neon glow around panel.
          boxShadow: const [
            BoxShadow(
              blurRadius: 18,
              spreadRadius: 1,
              color: Color(0x4D7B61FF),
              offset: Offset(0, 0),
            ),
          ],
          borderRadius: BorderRadius.circular(2),
        ),
        child: Center(
          child: Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ),
    );
  }
}

// Left scanning page.
class LeftEmptyPage extends StatelessWidget {
  // Constructor.
  const LeftEmptyPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: loginPageBackground,
      body: Stack(
        children: [
          // Fill page area.
          const SizedBox.expand(),
          // Top-left NFC panel.
          Align(
            alignment: Alignment.topLeft,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: loginPageBackground,
                  border: const Border.fromBorderSide(
                    BorderSide(color: Color(0xFF7B61FF), width: 1.5),
                  ),
                  boxShadow: const [
                    BoxShadow(
                      blurRadius: 18,
                      spreadRadius: 1,
                      color: Color(0x4D7B61FF),
                      offset: Offset(0, 0),
                    ),
                  ],
                  borderRadius: BorderRadius.circular(2),
                ),
                child: const Center(
                  child: Text(
                    'NFC',
                    style: TextStyle(color: Colors.white),
                  ),
                ),
              ),
            ),
          ),
          // Center content panel.
          Align(
            alignment: Alignment.center,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Container(
                height: 220,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: loginPageBackground,
                  border: const Border.fromBorderSide(
                    BorderSide(color: Color(0xFF7B61FF), width: 1.5),
                  ),
                  boxShadow: const [
                    BoxShadow(
                      blurRadius: 18,
                      spreadRadius: 1,
                      color: Color(0x4D7B61FF),
                      offset: Offset(0, 0),
                    ),
                  ],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ),
          // Bottom-left action button.
          Align(
            alignment: Alignment.bottomLeft,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _BackButton(
                label: 'Skandeer in',
                onPressed: () {},
              ),
            ),
          ),
          // Bottom-right back button.
          Align(
            alignment: Alignment.bottomRight,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _BackButton(
                label: 'Terug',
                onPressed: () => Navigator.pop(context),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// Right scanning page.
class RightEmptyPage extends StatelessWidget {
  // Constructor.
  const RightEmptyPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: loginPageBackground,
      body: Stack(
        children: [
          // Fill page area.
          const SizedBox.expand(),
          // Top-left dropdown panel.
          Align(
            alignment: Alignment.topLeft,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Container(
                decoration: BoxDecoration(
                  color: loginPageBackground,
                  border: const Border.fromBorderSide(
                    BorderSide(color: Color(0xFF7B61FF), width: 1.5),
                  ),
                  boxShadow: const [
                    BoxShadow(
                      blurRadius: 18,
                      spreadRadius: 1,
                      color: Color(0x4D7B61FF),
                      offset: Offset(0, 0),
                    ),
                  ],
                  borderRadius: BorderRadius.circular(2),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: DropdownButtonHideUnderline(
                  // Dropdown without underline.
                  child: DropdownButton<String>(
                    value: 'Opsie 1',
                    dropdownColor: loginPageBackground,
                    items: const [
                      DropdownMenuItem(
                        value: 'Opsie 1',
                        child: Text(
                          'Opsie 1',
                          style: TextStyle(color: Colors.white),
                        ),
                      ),
                      DropdownMenuItem(
                        value: 'Opsie 2',
                        child: Text(
                          'Opsie 2',
                          style: TextStyle(color: Colors.white),
                        ),
                      ),
                    ],
                    // Do nothing for now when option changes.
                    onChanged: (_) {},
                  ),
                ),
              ),
            ),
          ),
          // Center QR panel.
          Align(
            alignment: Alignment.center,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Container(
                height: 220,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: loginPageBackground,
                  border: const Border.fromBorderSide(
                    BorderSide(color: Color(0xFF7B61FF), width: 1.5),
                  ),
                  boxShadow: const [
                    BoxShadow(
                      blurRadius: 18,
                      spreadRadius: 1,
                      color: Color(0x4D7B61FF),
                      offset: Offset(0, 0),
                    ),
                  ],
                  borderRadius: BorderRadius.circular(2),
                ),
                child: const Center(
                  child: Text(
                    '(QR-kode, geldig vir 30 sekondes)',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white),
                  ),
                ),
              ),
            ),
          ),
          // Bottom-left back button.
          Align(
            alignment: Alignment.bottomLeft,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _BackButton(
                label: 'Terug',
                onPressed: () => Navigator.pop(context),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// Reusable back/action button wrapper.
class _BackButton extends StatelessWidget {
  // Button label text.
  final String label;
  // Function to call when pressed.
  final VoidCallback onPressed;

  // Constructor.
  const _BackButton({
    required this.label,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    // Reuse the gradient neon button style.
    return _GradientActionButton(
      label: label,
      onTap: onPressed,
      width: 160,
      height: 45,
    );
  }
}
