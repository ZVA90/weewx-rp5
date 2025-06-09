import sys
import queue
import syslog
import weewx.restx
import urllib.request, urllib.error
import weewx.units


# ============================================================================
#                            class StdRP5
# ============================================================================

class StdRP5(weewx.restx.StdRESTful):
    """RESTful class for RP5"""

    api_url = 'http://sgate.rp5.ru'
    protocol_name = 'RP5-API'

    def __init__(self, engine, config_dict):
        super(StdRP5, self).__init__(engine, config_dict)

        _rp5_dict = weewx.restx.get_site_dict(config_dict, 'RP5', 'api_key')
        if _rp5_dict is None:
            return
        _rp5_dict.setdefault('server_url', StdRP5.api_url)

        _manager_dict = weewx.manager.get_manager_dict_from_config(config_dict,
                                                                   'wx_binding')

        self.archive_queue = queue.Queue()
        self.archive_thread = RP5Thread(self.archive_queue,
                                        _manager_dict,
                                        protocol_name=StdRP5.protocol_name,
                                        **_rp5_dict)
        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        syslog.syslog(syslog.LOG_INFO, "rp5: %s: "
                                       "Data for api key %s will be uploaded" %
                      (StdRP5.protocol_name, _rp5_dict['api_key']))

    def new_archive_record(self, event):
        self.archive_queue.put(event.record)


# ============================================================================
#                           class RP5Thread
# ============================================================================

class RP5Thread(weewx.restx.RESTThread):
    """Class for posting data via RP5 API"""

    def __init__(self, queue, manager_dict, api_key, server_url,
                 protocol_name="Unknown-RESTful", post_interval=2,
                 max_backlog=sys.maxsize, stale=None, log_success=True,
                 log_failure=True, timeout=5, max_tries=3, retry_wait=2,
                 skip_upload=False):

        super(RP5Thread, self).__init__(queue,
                                             protocol_name=protocol_name,
                                             manager_dict=manager_dict,
                                             post_interval=post_interval,
                                             max_backlog=max_backlog,
                                             stale=stale,
                                             log_success=log_success,
                                             log_failure=log_failure,
                                             timeout=timeout,
                                             max_tries=max_tries,
                                             retry_wait=retry_wait,
                                             skip_upload=skip_upload)

        self.api_key = api_key
        self.server_url = server_url

    _FORMATS = {
            'dateTime':    'updated=%i',
            'outTemp':     't=%.1f',
            'outHumidity': 'u=%.0f',
            'barometer':   'p=%.1f',
            'windSpeed':   'ff=%.0f',
            'windDir':     'dd=%.0f',
            'windGust':    'ff10=%.0f',
            'rain':        'r=%.1f'
        }


    def format_url(self, incoming_record):
        """Return an URL for posting """

        record = weewx.units.to_METRICWX(incoming_record)
        _liststr = ["api_key=%s" % self.api_key]
        for _key in self._FORMATS:
            _v = record.get(_key)
            if _v is not None:
                try:
                    _liststr.append(self._FORMATS[_key] % _v)
                except TypeError:
                    syslog.syslog(syslog.LOG_ERR,
                                  "%s: format_url: Type error formatting value '%s' for key '%s'. Skipping." %
                                  (self.protocol_name, _v, _key))
        _urlquery = '&'.join(_liststr)
        _url = "%s/?%s" % (self.server_url, _urlquery)
        if weewx.debug >= 2:
            syslog.syslog(syslog.LOG_DEBUG, "restx: RP5-API: url: %s" % _url)
        return _url

    def post_request(self, request, data=None):
        try:
            _response = urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode(errors='ignore')
            except Exception as ex_read:
                error_body = f"Failed to read error body: {ex_read}"

            full_error_message = f"server returned HTTP {e.code} {e.reason}. Body: {error_body}"
            syslog.syslog(syslog.LOG_ERR, f"{self.protocol_name}: {full_error_message}")

            if e.code in [400, 401, 429]: # 401 for auth errors
                raise weewx.restx.FailedPost(full_error_message)
            else:
                raise # Re-raise the original urllib.error.HTTPError
        else:
            return _response
