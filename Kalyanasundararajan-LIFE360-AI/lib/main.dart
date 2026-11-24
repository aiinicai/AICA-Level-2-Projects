import 'screens/about_screen.dart';
import 'dart:async';

import 'package:material_ui/material_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'services/reminder_service.dart';
import 'screens/daily_planner.dart';
import 'screens/backup_recovery.dart';
import 'services/daily_schedule_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const Life360App());
}

class Life360App extends StatelessWidget {
  const Life360App({super.key, this.now});

  final DateTime Function()? now;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LIFE360 AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: Colors.teal, useMaterial3: true),
      home: LifeDashboard(now: now),
    );
  }
}

class LifeDashboard extends StatefulWidget {
  const LifeDashboard({super.key, this.now});

  final DateTime Function()? now;

  @override
  State<LifeDashboard> createState() => _LifeDashboardState();
}

class WellnessReminder {
  WellnessReminder({
    required this.id,
    required this.title,
    required this.icon,
    required this.message,
    required this.seconds,
  });

  final String id;
  final String title;
  final IconData icon;
  final String message;
  final ReminderService service = ReminderService();

  int seconds;
  bool saving = false;

  bool get active => service.isRunning;
}

class _LifeDashboardState extends State<LifeDashboard> {
  final SharedPreferencesAsync storage = SharedPreferencesAsync();
  final DailyScheduleService dailyScheduleService =
    DailyScheduleService();

bool checkingSchedules = false;

  bool isLoading = true;
  bool isSaving = false;
  bool remindersLoading = true;
  String? storageError;
  String activeDate = '';
  Timer? dailyResetTimer;

final ScrollController dashboardScrollController =
    ScrollController();

final GlobalKey remindersSectionKey = GlobalKey();

  final Map<String, bool> activities = {
    'Morning hydration': false,
    'Yoga / Physical exercise': false,
    'Meditation': false,
    'Medication check': false,
    'Plan work priorities': false,
    'Stand and stretch': false,
    'Evening walk': false,
    'Prepare for bedtime': false,
  };

  final Map<String, IconData> activityIcons = {
    'Morning hydration': Icons.water_drop,
    'Yoga / Physical exercise': Icons.fitness_center,
    'Meditation': Icons.self_improvement,
    'Medication check': Icons.medication,
    'Plan work priorities': Icons.work_outline,
    'Stand and stretch': Icons.accessibility_new,
    'Evening walk': Icons.directions_walk,
    'Prepare for bedtime': Icons.bedtime,
  };

  final Map<String, Color> activityColors = {
    'Morning hydration': Colors.blue,
    'Yoga / Physical exercise': Colors.green,
    'Meditation': Colors.purple,
    'Medication check': Colors.red,
    'Plan work priorities': Colors.brown,
    'Stand and stretch': Colors.teal,
    'Evening walk': Colors.orange,
    'Prepare for bedtime': Colors.indigo,
  };

  final Map<int, String> intervals = {
    10: '10 seconds (Testing only)',
    900: '15 minutes',
    1200: '20 minutes',
    1800: '30 minutes',
    2700: '45 minutes',
    3600: '60 minutes',
    7200: '120 minutes',
  };

  final List<WellnessReminder> reminders = [
    WellnessReminder(
      id: 'hydration',
      title: 'Drink water',
      icon: Icons.water_drop,
      message: 'Time for a hydration break!',
      seconds: 3600,
    ),
    WellnessReminder(
      id: 'stretch',
      title: 'Stand and Stretch',
      icon: Icons.accessibility_new,
      message: 'Time to stand and stretch! Take a short break.',
      seconds: 1800,
    ),
    WellnessReminder(
      id: 'eyes',
      title: 'Eye relaxation',
      icon: Icons.visibility,
      message: 'Rest your eyes and look away from the screen.',
      seconds: 1200,
    ),
    WellnessReminder(
      id: 'breathing',
      title: 'Mindful breathing',
      icon: Icons.self_improvement,
      message: 'Take a moment to relax and breathe gently.',
      seconds: 7200,
    ),
  ];

  @override
  void initState() {
    super.initState();
    loadActivities();
    loadReminderPreferences();
    dailyScheduleService.start(
  now: widget.now,
  onCheck: (now) {
    checkDailySchedules(now);
  },
);

    dailyResetTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => checkDateChange(),
    );
  }

  @override
  void dispose() {
    dailyResetTimer?.cancel();
dashboardScrollController.dispose();
    dailyScheduleService.dispose();

    for (final reminder in reminders) {
      reminder.service.dispose();
    }

    super.dispose();
  }

  String todayDate() {
    final now = widget.now?.call() ?? DateTime.now();
    return '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
  }

  String activityKey(String date, String activity) {
    return 'life360_${date}_$activity';
  }

  String reminderKey(WellnessReminder reminder) {
    return 'life360_reminder_${reminder.id}_seconds';
  }

  void notifyUser(String message) {
    if (!mounted) return;

    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> loadReminderPreferences() async {
    try {
      for (final reminder in reminders) {
        final saved = await storage.getInt(reminderKey(reminder));

        if (!mounted) return;

        if (saved != null && intervals.containsKey(saved)) {
          reminder.seconds = saved;
        }
      }
    } catch (_) {
      notifyUser('Unable to load reminder preferences.');
    } finally {
      if (mounted) {
        setState(() {
          remindersLoading = false;
        });
      }
    }
  }

  Future<void> saveReminderInterval(
    WellnessReminder reminder,
    int seconds,
  ) async {
    if (reminder.active || reminder.saving || !intervals.containsKey(seconds)) {
      return;
    }

    setState(() {
      reminder.saving = true;
    });

    try {
      await storage.setInt(reminderKey(reminder), seconds);

      if (!mounted) return;

      setState(() {
        reminder.seconds = seconds;
      });
    } catch (_) {
      notifyUser('Unable to save reminder preference.');
    } finally {
      if (mounted) {
        setState(() {
          reminder.saving = false;
        });
      }
    }
  }

  void toggleReminder(WellnessReminder reminder) {
    if (reminder.saving || remindersLoading) return;

    if (reminder.active) {
      reminder.service.stop();
      ScaffoldMessenger.of(context).clearSnackBars();
    } else {
      reminder.service.start(
        interval: Duration(seconds: reminder.seconds),
        onReminder: () {
          if (!mounted) return;

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              duration: const Duration(seconds: 5),
              content: Row(
                children: [
                  Icon(reminder.icon, color: Colors.white),
                  const SizedBox(width: 12),
                  Expanded(child: Text(reminder.message)),
                ],
              ),
            ),
          );
        },
      );
    }

    setState(() {});
  }

  void stopAllReminders() {
    for (final reminder in reminders) {
      reminder.service.stop();
    }

    ScaffoldMessenger.of(context).clearSnackBars();
    setState(() {});
  }

  Future<void> checkDailySchedules(DateTime now) async {
    if (!mounted || checkingSchedules) return;

    checkingSchedules = true;

    try {
      final activityList = activities.keys.toList();

      for (int i = 0; i < activityList.length; i++) {
        final enabled = await storage.getBool(
          'life360_schedule_${i}_enabled',
        );

        if (!mounted) return;
        if (enabled != true) continue;

        final minutes = await storage.getInt(
          'life360_schedule_${i}_minutes',
        );

        if (!mounted) return;

        if (minutes == null ||
            minutes < 0 ||
            minutes >= 1440) {
          continue;
        }

        final dateKey =
            '${now.year}-'
            '${now.month.toString().padLeft(2, '0')}-'
            '${now.day.toString().padLeft(2, '0')}';

        final occurrenceKey = '$dateKey|$minutes';

        final triggeredKey =
            'life360_schedule_${i}_last_triggered';

        final lastTriggered =
            await storage.getString(triggeredKey);

        if (!mounted) return;

        if (lastTriggered == occurrenceKey) continue;

        final shouldTrigger =
            dailyScheduleService.shouldTrigger(
          id: 'activity_$i',
          hour: minutes ~/ 60,
          minute: minutes % 60,
          now: now,
        );

        if (!shouldTrigger) continue;

        final activity = activityList[i];

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            duration: const Duration(seconds: 15),
            content: Row(
              children: [
                Icon(
                  activityIcons[activity],
                  color: Colors.white,
                  size: 32,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Reminder: $activity',
                    style: const TextStyle(fontSize: 18),
                  ),
                ),
              ],
            ),
          ),
        );

        await storage.setString(
          triggeredKey,
          occurrenceKey,
        );

        if (!mounted) return;
      }
    } catch (error) {
      debugPrint('Daily schedule error: $error');
    } finally {
      checkingSchedules = false;
    }
  }


  void checkDateChange() {
    if (!mounted || isLoading || isSaving) return;

    if (activeDate != todayDate()) {
      setState(() {
        isLoading = true;
      });

      loadActivities();
    }
  }

  Future<void> loadActivities() async {
    final today = todayDate();

    try {
      final restored = <String, bool>{};

      for (final activity in activities.keys) {
        restored[activity] =
            await storage.getBool(activityKey(today, activity)) ?? false;
      }

      if (!mounted) return;

      setState(() {
        activities.addAll(restored);
        activeDate = today;
        isLoading = false;
        storageError = null;
      });
    } catch (_) {
      if (!mounted) return;

      setState(() {
        isLoading = false;
        storageError = 'Unable to load saved activities.';
      });
    }
  }

  Future<void> updateActivity(String activity, bool value) async {
    if (isLoading || isSaving || storageError != null) {
      return;
    }

    if (activeDate != todayDate()) {
      setState(() {
        isLoading = true;
      });

      await loadActivities();
      return;
    }

    setState(() {
      isSaving = true;
    });

    try {
      await storage.setBool(activityKey(activeDate, activity), value);

      if (!mounted) return;

      setState(() {
        activities[activity] = value;
        isSaving = false;
      });
    } catch (_) {
      if (!mounted) return;

      setState(() {
        isSaving = false;
      });

      notifyUser('Unable to save activity. Please try again.');
    }
  }
    Widget buildWeeklyChart(Map<String, int> history) {
    final entries = history.entries.toList().reversed.toList();

    const weekdays = [
      'Mon', 'Tue', 'Wed', 'Thu',
      'Fri', 'Sat', 'Sun',
    ];

    return Column(
      children: [
        const Text(
          'Weekly Activity Performance',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 20),
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: entries.map((entry) {
            final day = DateTime.parse(entry.key);
            final progress = entry.value / activities.length;
            final isToday = entry.key == history.keys.first;

            final color = isToday
                ? Colors.teal
                : Colors.blue;

            return Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 3,
                ),
                child: Column(
                  children: [
                    Text(
                      '${entry.value}',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Container(
                      height: 120,
                      width: 28,
                      decoration: BoxDecoration(
                        color: color.withAlpha(30),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      alignment: Alignment.bottomCenter,
                      child: Container(
                        height: 120 * progress,
                        decoration: BoxDecoration(
                          color: color,
                          borderRadius: BorderRadius.circular(6),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      weekdays[day.weekday - 1],
                      style: const TextStyle(fontSize: 11),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: 12),
        const Text('Activities completed each day'),
      ],
    );
  }


  Widget buildReportCircle(
    String label,
    int completed,
    int total,
    Color color,
  ) {
    final progress = total == 0 ? 0.0 : completed / total;

    return Expanded(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 100,
            height: 100,
            child: Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 100,
                  height: 100,
                  child: CircularProgressIndicator(
                    value: progress,
                    strokeWidth: 10,
                    backgroundColor: color.withAlpha(35),
                    valueColor:
                        AlwaysStoppedAnimation<Color>(color),
                  ),
                ),
                Text(
                  '${(progress * 100).round()}%',
                  style: const TextStyle(
                    fontSize: 23,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '$completed / $total',
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }


  Future<void> showActivityHistory() async {
    final now = widget.now?.call() ?? DateTime.now();
    final history = <String, int>{};

    try {
      for (int i = 0; i < 7; i++) {
        final day = DateTime(now.year, now.month, now.day - i);

        final date =
            '${day.year}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}';

        int completed = 0;

        for (final activity in activities.keys) {
          final saved = await storage.getBool(activityKey(date, activity));

          if (saved == true) completed++;
        }

        history[date] = completed;
      }

      if (!mounted) return;

      await showDialog<void>(
        context: context,
        builder: (dialogContext) {
          return AlertDialog(
            title: const Text('7-Day Activity History'),
            content: SizedBox(
              width: 450,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
  Row(
    children: [
      buildReportCircle(
        'Today',
        history.values.first,
        activities.length,
        Colors.teal,
      ),
      buildReportCircle(
        'Last 7 days',
        history.values.fold<int>(
          0,
          (sum, value) => sum + value,
        ),
        activities.length * 7,
        Colors.purple,
      ),
    ],
  ),
  const SizedBox(height: 20),
  const Divider(),
  const SizedBox(height: 12),
  const Text(
    'Daily Performance',
    style: TextStyle(
      fontSize: 18,
      fontWeight: FontWeight.bold,
    ),
  ),
  const SizedBox(height: 16),
  buildWeeklyChart(history),
const SizedBox(height: 20),
const Divider(),
const SizedBox(height: 12),
...history.entries.map((entry) {
                    final progress = entry.value / activities.length;

                    return Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(entry.key),
                          const SizedBox(height: 6),
                          Text(
                            '${entry.value} of ${activities.length} completed '
                            '(${(progress * 100).toStringAsFixed(1)}%)',
                          ),
                          const SizedBox(height: 6),
                          LinearProgressIndicator(
                            value: progress,
                            minHeight: 12,
                            borderRadius: BorderRadius.circular(8),
                          ),
                        ],
                      ),
                    );
                    }),
],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.of(dialogContext).pop();
                },
                child: const Text('Close'),
              ),
            ],
          );
        },
      );
    } catch (_) {
      notifyUser('Unable to load activity history.');
    }
  }
    Widget buildNavigationButton(
    IconData icon,
    String label,
    Color color,
    VoidCallback onPressed,
  ) {
    return Expanded(
      child: TextButton(
        onPressed: onPressed,
        style: TextButton.styleFrom(
          foregroundColor: color,
          padding: const EdgeInsets.symmetric(
            vertical: 4,
            horizontal: 2,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 28,
              color: color,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              maxLines: 1,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }


  void goToHome() {
    if (dashboardScrollController.hasClients) {
      dashboardScrollController.animateTo(
        0,
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOut,
      );
    }
  }

  void goToReminders() {
    final sectionContext = remindersSectionKey.currentContext;

    if (sectionContext != null) {
      Scrollable.ensureVisible(
        sectionContext,
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOut,
      );
    } else if (dashboardScrollController.hasClients) {
      dashboardScrollController.animateTo(
        dashboardScrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOut,
      );
    }
  }


    Widget buildActivityCard(String activity) {
    final color = activityColors[activity] ?? Colors.teal;
    final completed = activities[activity] ?? false;

    return Card(
      elevation: 1,
      margin: EdgeInsets.zero,
      color: color.withValues(alpha: 0.07),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(22),
        side: BorderSide(
          color: color.withValues(
            alpha: completed ? 0.55 : 0.15,
          ),
          width: completed ? 2 : 1,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: isSaving
            ? null
            : () => updateActivity(activity, !completed),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircleAvatar(
                radius: 32,
                backgroundColor:
                    color.withValues(alpha: 0.14),
                child: Icon(
                  activityIcons[activity],
                  color: color,
                  size: 38,
                ),
              ),
              const SizedBox(height: 8),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                controlAffinity:
                    ListTileControlAffinity.trailing,
                activeColor: color,
                title: Text(
                  activity,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                value: completed,
                onChanged: isSaving
                    ? null
                    : (value) {
                        updateActivity(
                          activity,
                          value ?? false,
                        );
                      },
              ),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(
                  vertical: 10,
                  horizontal: 6,
                ),
                decoration: BoxDecoration(
                  color: completed
                      ? Colors.teal.shade800
                      : Colors.white,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisAlignment:
                      MainAxisAlignment.center,
                  children: [
                    Icon(
                      completed
                          ? Icons.check_circle
                          : Icons.touch_app,
                      color: completed
                          ? Colors.white
                          : color,
                      size: 22,
                    ),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        completed
                            ? 'Completed'
                            : 'Mark Done',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: completed
                              ? Colors.white
                              : color,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget buildActivityGrid() {
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns =
            constraints.maxWidth >= 650 ? 3 :
            constraints.maxWidth >= 340 ? 2 : 1;

        return GridView.count(
          crossAxisCount: columns,
          shrinkWrap: true,
          physics:
              const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          mainAxisExtent: 230,
          children: activities.keys
              .map(buildActivityCard)
              .toList(),
        );
      },
    );
  }

Widget buildReminderCard(WellnessReminder reminder) {
     return Card(
      child: ExpansionTile(
        leading: Icon(reminder.icon, color: Colors.teal, size: 30),
        title: Text(reminder.title),
        subtitle: Text(
          reminder.active ? 'Active' : 'Inactive',
          style: TextStyle(color: reminder.active ? Colors.teal : Colors.grey),
        ),
        childrenPadding: const EdgeInsets.all(16),
        children: [
          DropdownButtonFormField<int>(
            key: ValueKey('${reminder.id}_${reminder.seconds}'),
            initialValue: reminder.seconds,
            isExpanded: true,
            decoration: const InputDecoration(
              labelText: 'Reminder frequency',
              border: OutlineInputBorder(),
            ),
            items: intervals.entries.map((entry) {
              return DropdownMenuItem<int>(
                value: entry.key,
                child: Text(entry.value),
              );
            }).toList(),
            onChanged: reminder.active || reminder.saving || remindersLoading
                ? null
                : (value) {
                    if (value != null) {
                      saveReminderInterval(reminder, value);
                    }
                  },
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton.icon(
              onPressed: remindersLoading || reminder.saving
                  ? null
                  : () => toggleReminder(reminder),
              icon: Icon(
                reminder.active ? Icons.stop : Icons.notifications_active,
              ),
              label: Text(reminder.active ? 'Stop Reminder' : 'Start Reminder'),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final completed = activities.values.where((value) => value).length;

    final progress = completed / activities.length;

        return Scaffold(
      bottomNavigationBar: SafeArea(
        child: BottomAppBar(
  height: 100,
          child: Row(
            mainAxisAlignment:
                MainAxisAlignment.spaceAround,
            children: [
              buildNavigationButton(
                Icons.home_rounded,
                'Home',
                Colors.teal,
                goToHome,
              ),
              buildNavigationButton(
                Icons.calendar_month,
                'Planner',
                Colors.blue,
                () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (context) =>
                          const DailyPlanner(),
                    ),
                  );
                },
              ),
              buildNavigationButton(
                Icons.notifications_active,
                'Reminders',
                Colors.orange.shade800,
                goToReminders,
              ),
              buildNavigationButton(
                Icons.bar_chart_rounded,
                'Reports',
                Colors.purple,
                () {
  if (!isLoading && !isSaving) {
    showActivityHistory();
  }
},
              ),
            ],
          ),
        ),
      ),
            appBar: AppBar(
        title: const Text('LIFE360 AI'),
        backgroundColor:
            Theme.of(context).colorScheme.primaryContainer,
        actions: [
          IconButton(
            icon: const Icon(Icons.verified_user_outlined),
            tooltip: 'Backup & Recovery',
            onPressed: () async {
              await Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => const BackupRecovery(),
                ),
              );

              if (!mounted) return;

              for (final reminder in reminders) {
                reminder.service.stop();
              }

              await loadActivities();

              if (!mounted) return;

              await loadReminderPreferences();
            },
          ),
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: '7-Day Activity History',
            onPressed: isLoading || isSaving
                ? null
                : showActivityHistory,
          ),
          IconButton(
            icon: const Icon(Icons.info_outline),
            tooltip: 'About LIFE360 AI',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => const AboutScreen(),
                ),
              );
            },
          ),
        ],
      ),
      body: isLoading
          ? const Center(
              child: CircularProgressIndicator(),
            )
          : storageError != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(storageError!),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: () {
                          setState(() {
                            isLoading = true;
                          });

                          loadActivities();
                        },
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : Center(
                  child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 850),
                child: ListView(
  controller: dashboardScrollController,
                  padding: const EdgeInsets.all(24),
                  children: [
                    const Text(
                      'Your Intelligent Daily Life Companion',
                      style: TextStyle(
                        fontSize: 25,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Health \u2022 Work \u2022 Wellness \u2022 Relaxation',
                    ),
                    const SizedBox(height: 8),
                    Text('Date: $activeDate'),
                    const SizedBox(height: 16),
SizedBox(
  width: double.infinity,
  height: 65,
  child: FilledButton.icon(
    onPressed: () async {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (context) => const DailyPlanner(),
        ),
      );
    },
    icon: const Icon(
      Icons.calendar_month,
      size: 32,
    ),
    label: const Text(
      'My Daily Planner',
      style: TextStyle(
        fontSize: 20,
        fontWeight: FontWeight.bold,
      ),
    ),
  ),
),
                    const SizedBox(height: 16),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Row(
                          children: [
                            SizedBox(
                              width: 76,
                              height: 76,
                              child: Stack(
                                alignment: Alignment.center,
                                children: [
                                  SizedBox.expand(
                                    child: CircularProgressIndicator(
                                      value: progress,
                                      strokeWidth: 8,
                                      backgroundColor: Colors.teal.withValues(
                                        alpha: 0.12,
                                      ),
                                    ),
                                  ),
                                  Text(
                                    '${(progress * 100).round()}%',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 18,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 20),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '$completed of ${activities.length} activities completed',
                                    style: const TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                  LinearProgressIndicator(
                                    value: progress,
                                    minHeight: 12,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    isSaving
                                        ? 'Saving progress...'
                                        : 'Progress stored locally',
                                    style: const TextStyle(color: Colors.teal),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      "Today's Activities",
                      style: TextStyle(
                        fontSize: 21,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    buildActivityGrid(),
                    const SizedBox(height: 24),
                    Text(
  'Smart Wellness Reminder',
  key: remindersSectionKey,
                      style: TextStyle(
                        fontSize: 21,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text('Tap a reminder to choose its frequency.'),
                    const SizedBox(height: 8),
                    ...reminders.map(buildReminderCard),
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: reminders.any((reminder) => reminder.active)
                          ? stopAllReminders
                          : null,
                      icon: const Icon(Icons.stop_circle),
                      label: const Text('Stop All Reminders'),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Reminders work while the application is running. '
                      'Selected intervals are saved on this device.',
                      style: TextStyle(fontSize: 13),
                    ),
                    const SizedBox(height: 16),
                  ],
                ),
              ),
            ),
    );
  }
}

