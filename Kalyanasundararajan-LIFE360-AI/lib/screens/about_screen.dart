import 'package:material_ui/material_ui.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  Widget informationCard({
    required IconData icon,
    required String title,
    required String description,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: Colors.teal, size: 28),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              description,
              style: const TextStyle(
                fontSize: 15,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('About LIFE360 AI'),
        backgroundColor:
            Theme.of(context).colorScheme.primaryContainer,
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 750),
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              const Icon(
                Icons.auto_awesome,
                size: 80,
                color: Colors.teal,
              ),
              const SizedBox(height: 16),
              const Text(
                'LIFE360 AI',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 36,
                  fontWeight: FontWeight.bold,
                  color: Colors.teal,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Your Intelligent Daily Life Companion',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 18),
              ),
              const SizedBox(height: 12),
              const Center(
                child: Chip(
                  label: Text('Version 1.1.0'),
                ),
              ),
              const SizedBox(height: 24),
              informationCard(
                icon: Icons.lightbulb_outline,
                title: 'Our Vision',
                description:
                    'Empowering individuals to live healthier, '
                    'more productive, organized and balanced lives '
                    'through intelligent daily life management.',
              ),
              informationCard(
                icon: Icons.dashboard_outlined,
                title: 'Product Overview',
                description:
                    'LIFE360 AI brings daily activities, wellness '
                    'reminders, personal planning, progress tracking, '
                    'activity history and backup recovery into '
                    'one integrated application.',
              ),
              informationCard(
                icon: Icons.person_outline,
                title: 'Concept, Design & Development',
                description:
                    'CA Kalyanasundararajan Kaleeswaran\n\n'
                    'Capstone Project - 2026\n\n'
                    'Designed with a focus on simplicity, '
                    'personal productivity, privacy and '
                    'balanced living.',
              ),
              informationCard(
                icon: Icons.verified_user_outlined,
                title: 'Privacy & Data Protection',
                description:
                    'Application records are stored locally. '
                    'Users can create, validate and restore '
                    'their personal backups. Exported backup '
                    'files are not encrypted and should be '
                    'stored securely.',
              ),
              informationCard(
                icon: Icons.devices,
                title: 'Technology & Compatibility',
                description:
                    'Built using Flutter and Dart with a '
                    'cross-platform architecture. '
                    'Version 1.1 is being verified on the web. '
                    'Additional device compatibility is subject '
                    'to platform-specific testing.',
              ),
              informationCard(
                icon: Icons.health_and_safety_outlined,
                title: 'Important Disclaimer',
                description:
                    'LIFE360 AI is a personal wellness and '
                    'productivity management application. '
                    'It does not provide medical diagnosis, '
                    'treatment or professional medical advice. '
                    'Reminders should not replace essential '
                    'medical or emergency alert systems.',
              ),
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 16),
              const Text(
                '\u00A9 2026 CA Kalyanasundararajan Kaleeswaran',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 15,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'All rights reserved.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              const Text(
                'Live Better. Work Smarter. Stay Balanced.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.teal,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
