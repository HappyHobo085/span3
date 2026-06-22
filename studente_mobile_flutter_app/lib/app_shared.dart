import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ─── Color tokens ────────────────────────────────────────────────────────────
const Color kBg        = Color(0xFF0A0F1E);
const Color kSurface1  = Color(0x0AFFFFFF); // 4 % white
const Color kBorder    = Color(0x337B61FF); // 20 % purple
const Color kBorderEm  = Color(0x737B61FF); // 45 % purple
const Color kAccent    = Color(0xFF7B61FF);
const Color kAccent2   = Color(0xFF00C2FF);
const Color kText1     = Color(0xFFFFFFFF);
const Color kText2     = Color(0x99FFFFFF); // 60 %
const Color kTextMuted = Color(0x59FFFFFF); // 35 %
const Color kSuccess   = Color(0xFF10B981);

// Keep old names so existing files compile until they are updated in Tasks 9-14.
const Color loginPageBackground = kBg;
const Color loginDarkBlue       = Color(0xFF0E1E3B);
const Color loginBrown          = Color(0xFF935E28);

// ─── Gradient decoration helper ──────────────────────────────────────────────
const LinearGradient kGradient = LinearGradient(
  colors: [kAccent, kAccent2],
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
);

BoxDecoration kGlassDecoration({
  double radius = 12,
  Color? borderColor,
}) =>
    BoxDecoration(
      color: kSurface1,
      border: Border.all(color: borderColor ?? kBorder, width: 1.5),
      borderRadius: BorderRadius.circular(radius),
      boxShadow: const [
        BoxShadow(
          color: Color(0x147B61FF), // 8 % purple
          blurRadius: 24,
          spreadRadius: 0,
        ),
      ],
    );

// ─── AppScreenHeader ─────────────────────────────────────────────────────────
/// Consistent header at the top of every role screen.
class AppScreenHeader extends StatelessWidget {
  final String title;
  final String? subtitle;
  final bool showBack;
  final Widget? trailing;

  const AppScreenHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.showBack = false,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: Color(0x0AFFFFFF), width: 1)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle!,
                    style: GoogleFonts.inter(color: kTextMuted, fontSize: 11),
                  ),
                ],
              ],
            ),
          ),
          if (trailing != null) trailing!,
          if (showBack)
            GestureDetector(
              onTap: () => Navigator.pop(context),
              child: Text(
                '← Terug',
                style: GoogleFonts.inter(
                  color: kAccent,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

// ─── NfcStatusBadge ──────────────────────────────────────────────────────────
class NfcStatusBadge extends StatelessWidget {
  const NfcStatusBadge({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(
        color: const Color(0x1F10B981),
        border: Border.all(color: const Color(0x4D10B981), width: 1),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: const BoxDecoration(
              color: kSuccess,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 5),
          Text(
            'NFC Gereed',
            style: GoogleFonts.inter(
              color: const Color(0xFF6EE7B7),
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

// ─── GlassCard ───────────────────────────────────────────────────────────────
/// A container with the glassmorphism dark card style.
class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final double radius;
  final Color? borderColor;

  const GlassCard({
    super.key,
    required this.child,
    this.padding,
    this.radius = 12,
    this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: kGlassDecoration(radius: radius, borderColor: borderColor),
      padding: padding,
      child: child,
    );
  }
}

// ─── GlassTapPanel ───────────────────────────────────────────────────────────
/// Full-height tappable panel used on role home screens.
class GlassTapPanel extends StatelessWidget {
  final String label;
  final String? subtitle;
  final String? icon;
  final VoidCallback onTap;
  final Color? borderColor;

  const GlassTapPanel({
    super.key,
    required this.label,
    this.subtitle,
    this.icon,
    required this.onTap,
    this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Container(
        decoration: kGlassDecoration(radius: 14, borderColor: borderColor),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (icon != null) ...[
              Text(icon!, style: const TextStyle(fontSize: 26)),
              const SizedBox(height: 10),
            ],
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text(
                label,
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(
                  color: kText1,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  height: 1.3,
                ),
              ),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 4),
              Text(
                subtitle!,
                style: GoogleFonts.inter(color: kTextMuted, fontSize: 10),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ─── GlassInput ──────────────────────────────────────────────────────────────
class GlassInput extends StatelessWidget {
  final TextEditingController? controller;
  final String? hintText;
  final bool obscureText;
  final Widget? prefixIcon;
  final TextInputType? keyboardType;

  const GlassInput({
    super.key,
    this.controller,
    this.hintText,
    this.obscureText = false,
    this.prefixIcon,
    this.keyboardType,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: kGlassDecoration(radius: 8),
      child: TextField(
        controller: controller,
        obscureText: obscureText,
        keyboardType: keyboardType,
        style: GoogleFonts.inter(color: kText1, fontSize: 13),
        decoration: InputDecoration(
          hintText: hintText,
          hintStyle: GoogleFonts.inter(color: kTextMuted, fontSize: 13),
          prefixIcon: prefixIcon,
          border: InputBorder.none,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
        ),
      ),
    );
  }
}

// ─── GlassSearchRow ──────────────────────────────────────────────────────────
class GlassSearchRow extends StatelessWidget {
  const GlassSearchRow({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: kGlassDecoration(radius: 8),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      child: Row(
        children: [
          const Icon(Icons.search, color: kTextMuted, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: TextField(
              style: GoogleFonts.inter(color: kText1, fontSize: 12),
              decoration: InputDecoration(
                hintText: 'Soek...',
                hintStyle: GoogleFonts.inter(color: kTextMuted, fontSize: 12),
                border: InputBorder.none,
                isDense: true,
                contentPadding: EdgeInsets.zero,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── GlassSelect ─────────────────────────────────────────────────────────────
class GlassSelect<T> extends StatelessWidget {
  final T value;
  final List<DropdownMenuItem<T>> items;
  final ValueChanged<T?> onChanged;

  const GlassSelect({
    super.key,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: kGlassDecoration(radius: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<T>(
          value: value,
          items: items,
          onChanged: onChanged,
          dropdownColor: const Color(0xFF1A1D2E),
          style: GoogleFonts.inter(color: kText1, fontSize: 12),
          icon: const Icon(Icons.expand_more, color: kTextMuted, size: 18),
        ),
      ),
    );
  }
}

// ─── GradientActionButton ────────────────────────────────────────────────────
/// Primary action button with purple→cyan gradient.
class GradientActionButton extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  final double? width;
  final double height;

  const GradientActionButton({
    super.key,
    required this.label,
    required this.onTap,
    this.width,
    this.height = 46,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          gradient: kGradient,
          borderRadius: BorderRadius.circular(10),
          boxShadow: const [
            BoxShadow(
              color: Color(0x807B61FF),
              blurRadius: 24,
              offset: Offset(0, 4),
            ),
          ],
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: GoogleFonts.inter(
            color: Colors.white,
            fontSize: 13,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

// ─── OutlineActionButton ─────────────────────────────────────────────────────
class OutlineActionButton extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  final double? width;
  final double height;

  const OutlineActionButton({
    super.key,
    required this.label,
    required this.onTap,
    this.width,
    this.height = 46,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          border: Border.all(color: kBorderEm, width: 1),
          borderRadius: BorderRadius.circular(10),
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: GoogleFonts.inter(
            color: kText2,
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }
}
