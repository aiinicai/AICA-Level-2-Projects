import 'package:material_ui/material_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DailyPlanner extends StatefulWidget {
  const DailyPlanner({super.key});

  @override
  State<DailyPlanner> createState() => _DailyPlannerState();
}

class _DailyPlannerState extends State<DailyPlanner> {
  final SharedPreferencesAsync storage = SharedPreferencesAsync();

  bool isLoading = true;
  bool isSaving = false;
  String? error;

  final List<String> activities = [
    'Morning hydration',
    'Yoga / Physical exercise',
    'Meditation',
    'Medication check',
    'Plan work priorities',
    'Stand and stretch',
    'Evening walk',
    'Prepare for bedtime',
  ];

  final List<IconData> icons = [
    Icons.water_drop,
    Icons.fitness_center,
    Icons.self_improvement,
    Icons.medication,
    Icons.work_outline,
    Icons.accessibility_new,
    Icons.directions_walk,
    Icons.bedtime,
  ];

  final List<Color> colors = [
    Colors.blue,
    Colors.green,
    Colors.purple,
    Colors.red,
    Colors.brown,
    Colors.teal,
    Colors.orange,
    Colors.indigo,
  ];

  final Map<int, TimeOfDay> times = {};
  final Map<int, bool> enabled = {};

  @override
  void initState() {
    super.initState();
    loadSchedules();
  }

  String scheduleKey(int index) {
    return 'life360_schedule_${index}_minutes';
  }

  String enabledKey(int index) {
    return 'life360_schedule_${index}_enabled';
  }

  Future<void> loadSchedules() async {
    try {
      final restoredTimes = <int, TimeOfDay>{};
      final restoredEnabled = <int, bool>{};

      for (int i = 0; i < activities.length; i++) {
        final minutes = await storage.getInt(scheduleKey(i));

        if (minutes != null && minutes >= 0 && minutes < 1440) {
          restoredTimes[i] = TimeOfDay(
            hour: minutes ~/ 60,
            minute: minutes % 60,
          );
        }

        restoredEnabled[i] =
            restoredTimes.containsKey(i) &&
            (await storage.getBool(enabledKey(i)) ?? false);
      }

      if (!mounted) return;

      setState(() {
        times
          ..clear()
          ..addAll(restoredTimes);

        enabled
          ..clear()
          ..addAll(restoredEnabled);

        isLoading = false;
        error = null;
      });
    } catch (_) {
      if (!mounted) return;

      setState(() {
        isLoading = false;
        error = 'Unable to load your schedules.';
      });
    }
  }

  void showMessage(String message) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  Future<void> selectTime(int index) async {
    if (isSaving) return;

    final selected = await showTimePicker(
      context: context,
      initialTime: times[index] ?? TimeOfDay.now(),
      helpText: 'Choose reminder time',
    );

    if (selected == null || !mounted) return;

    setState(() {
      isSaving = true;
    });

    try {
      await storage.setInt(
        scheduleKey(index),
        selected.hour * 60 + selected.minute,
      );

      if (!mounted) return;

      setState(() {
        times[index] = selected;
      });

      showMessage('Time saved successfully.');
    } catch (_) {
      showMessage('Unable to save time. Please try again.');
    } finally {
      if (mounted) {
        setState(() {
          isSaving = false;
        });
      }
    }
  }

  Future<void> toggleSchedule(int index, bool value) async {
    if (isSaving) return;

    if (value && !times.containsKey(index)) {
      showMessage('Please select a time first.');
      return;
    }

    setState(() {
      isSaving = true;
    });

    try {
      await storage.setBool(enabledKey(index), value);

      if (!mounted) return;

      setState(() {
        enabled[index] = value;
      });
    } catch (_) {
      showMessage('Unable to save reminder setting.');
    } finally {
      if (mounted) {
        setState(() {
          isSaving = false;
        });
      }
    }
  }

  Widget buildScheduleCard(int index) {
    final color = colors[index];
    final active = enabled[index] ?? false;
    final time = times[index];

    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 30,
                  backgroundColor: color.withValues(alpha: 0.12),
                  child: Icon(
                    icons[index],
                    size: 34,
                    color: color,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Text(
                    activities[index],
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 56,
              child: OutlinedButton.icon(
                onPressed: isSaving
                    ? null
                    : () => selectTime(index),
                icon: const Icon(Icons.access_time, size: 26),
                label: Text(
                  time == null
                      ? 'Set Time'
                      : time.format(context),
                  style: const TextStyle(fontSize: 20),
                ),
              ),
            ),
            const SizedBox(height: 8),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              secondary: Icon(
                active
                    ? Icons.notifications_active
                    : Icons.notifications_off,
                color: active ? Colors.teal : Colors.grey,
                size: 28,
              ),
              title: Text(
                active ? 'Reminder ON' : 'Reminder OFF',
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                ),
              ),
              value: active,
              onChanged: isSaving
                  ? null
                  : (value) => toggleSchedule(index, value),
            ),
            if (index == 3)
              const Text(
                'Use only your prescribed medication timings. '
                'Keep a separate reliable medication alarm.',
                style: TextStyle(fontSize: 13),
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final activeCount =
        enabled.values.where((value) => value).length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Daily Planner'),
        backgroundColor:
            Theme.of(context).colorScheme.primaryContainer,
      ),
      body: isLoading
          ? const Center(
              child: CircularProgressIndicator(),
            )
          : error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(error!),
                      const SizedBox(height: 16),
                      ElevatedButton.icon(
                        onPressed: () {
                          setState(() {
                            isLoading = true;
                          });
                          loadSchedules();
                        },
                        icon: const Icon(Icons.refresh),
                        label: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(
                      maxWidth: 850,
                    ),
                    child: ListView(
                      padding: const EdgeInsets.all(20),
                      children: [
                        const Icon(
                          Icons.calendar_month,
                          size: 64,
                          color: Colors.teal,
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'Plan Your Day',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Choose a time and switch on your reminder.',
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 16),
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(18),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.notifications_active,
                                  color: Colors.teal,
                                  size: 32,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    '$activeCount of 8 reminders enabled',
                                    style: const TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        ...List.generate(
                          activities.length,
                          buildScheduleCard,
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'Schedules are stored on this device. '
                          'Scheduled alerts require the scheduling '
                          'engine to be connected and the app running.',
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 20),
                      ],
                    ),
                  ),
                ),
    );
  }
}