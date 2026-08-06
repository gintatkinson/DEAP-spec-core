import 'package:flutter/material.dart';
import 'package:app_flutter/data/remote/gnmi_telemetry_client.dart';

/// Realises: [UC-05/TelemetryInjectionPanel]
/// UI widget for monitoring and manually injecting gNMI telemetry metrics.
///
/// Exists to provide operators and developers with an interactive panel to simulate
/// live telemetry updates, test stream listeners, and verify UI responsiveness under
/// dynamic network updates.
class TelemetryInjectionPanel extends StatefulWidget {
  /// Optional [GnmiTelemetryClient] instance. If omitted, a default client is created.
  final GnmiTelemetryClient? client;

  /// Callback triggered whenever a telemetry update is injected.
  final void Function(GnmiTelemetryUpdate update)? onTelemetryInjected;

  /// Creates a [TelemetryInjectionPanel].
  const TelemetryInjectionPanel({
    super.key,
    this.client,
    this.onTelemetryInjected,
  });

  @override
  State<TelemetryInjectionPanel> createState() => _TelemetryInjectionPanelState();
}

class _TelemetryInjectionPanelState extends State<TelemetryInjectionPanel> {
  late final GnmiTelemetryClient _client;
  final TextEditingController _pathController = TextEditingController(
    text: '/interfaces/interface[name=eth0]/state/counters/in-octets',
  );
  final TextEditingController _valueController = TextEditingController(text: '102400');
  final List<GnmiTelemetryUpdate> _recentUpdates = [];
  bool _isStreaming = false;

  @override
  void initState() {
    super.initState();
    _client = widget.client ?? GnmiTelemetryClient();
    _isStreaming = _client.isConnected;
  }

  @override
  void dispose() {
    _pathController.dispose();
    _valueController.dispose();
    super.dispose();
  }

  void _toggleStream() {
    setState(() {
      if (_isStreaming) {
        _client.disconnectStream();
        _isStreaming = false;
      } else {
        _client.connectStream();
        _isStreaming = true;
      }
    });
  }

  void _injectTelemetry() {
    final path = _pathController.text.trim();
    final rawValue = _valueController.text.trim();
    final parsedValue = num.tryParse(rawValue) ?? rawValue;

    final update = GnmiTelemetryUpdate(
      path: path.isNotEmpty ? path : '/telemetry/metric',
      value: parsedValue,
    );

    if (_client.isConnected) {
      _client.injectUpdate(update);
    }

    setState(() {
      _recentUpdates.insert(0, update);
      if (_recentUpdates.length > 20) {
        _recentUpdates.removeLast();
      }
    });

    widget.onTelemetryInjected?.call(update);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.all(12.0),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Telemetry Injection Panel',
                  style: theme.textTheme.titleMedium,
                ),
                Chip(
                  label: Text(_isStreaming ? 'Streaming' : 'Disconnected'),
                  backgroundColor: _isStreaming ? Colors.green.shade100 : Colors.grey.shade200,
                  side: BorderSide.none,
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _pathController,
              decoration: const InputDecoration(
                labelText: 'gNMI Target Path',
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _valueController,
              decoration: const InputDecoration(
                labelText: 'Metric Value',
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                ElevatedButton.icon(
                  onPressed: _toggleStream,
                  icon: Icon(_isStreaming ? Icons.stop : Icons.play_arrow),
                  label: Text(_isStreaming ? 'Disconnect' : 'Connect Stream'),
                ),
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  key: const Key('inject_telemetry_button'),
                  onPressed: _injectTelemetry,
                  icon: const Icon(Icons.send),
                  label: const Text('Inject Metric'),
                ),
              ],
            ),
            if (_recentUpdates.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(
                'Recent Updates:',
                style: theme.textTheme.labelMedium,
              ),
              const SizedBox(height: 4),
              SizedBox(
                height: 120,
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: _recentUpdates.length,
                  itemBuilder: (context, index) {
                    final u = _recentUpdates[index];
                    return Text(
                      '${u.timestamp.toIso8601String().substring(11, 19)} - ${u.path}: ${u.value}',
                      style: theme.textTheme.bodySmall,
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
