#property copyright "Private market desk"
#property version   "1.10"
#property description "Read-only dump of account and quotes. Does not send orders."
#property script_show_inputs

input int TimerSeconds = 1;
input string WatchCSV = "EURUSD,XAUUSD,XAGUSD,XTIUSD,US30,BTCUSD,ETHUSD,GBPUSD";
datetime last_symbols_dump = 0;
datetime last_rates_dump = 0;
datetime last_deals_dump = 0;

void OnStart()
  {
   FolderCreate("desk", FILE_COMMON);
   while(!IsStopped())
     {
      ProcessMarketRequest();
      DumpAccount();
      DumpPositions();
      datetime now = TimeLocal();
      if(last_deals_dump==0 || now-last_deals_dump>=15)
        {
         DumpDeals();
         last_deals_dump = now;
        }
      if(last_symbols_dump==0 || now-last_symbols_dump>=60)
        {
         DumpSymbols();
         last_symbols_dump = now;
        }
      if(last_rates_dump==0 || now-last_rates_dump>=30)
        {
         DumpRates();
         last_rates_dump = now;
        }
      Sleep((int)MathMax(TimerSeconds, 1) * 1000);
     }
  }

int OpenCsv(const string name)
  {
   return FileOpen("desk\\"+name, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
  }

void DumpAccount()
  {
   int h = OpenCsv("account.csv");
   if(h == INVALID_HANDLE)
      return;
   FileWrite(h, "login", IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)));
   FileWrite(h, "name", AccountInfoString(ACCOUNT_NAME));
   FileWrite(h, "server", AccountInfoString(ACCOUNT_SERVER));
   FileWrite(h, "currency", AccountInfoString(ACCOUNT_CURRENCY));
   FileWrite(h, "balance", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2));
   FileWrite(h, "equity", DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2));
   FileWrite(h, "margin", DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN), 2));
   FileWrite(h, "margin_free", DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE), 2));
   FileWrite(h, "profit", DoubleToString(AccountInfoDouble(ACCOUNT_PROFIT), 2));
   FileWrite(h, "leverage", IntegerToString(AccountInfoInteger(ACCOUNT_LEVERAGE)));
   FileClose(h);
  }

void DumpPositions()
  {
   int h = OpenCsv("positions.csv");
   if(h == INVALID_HANDLE)
      return;
   FileWrite(h, "ticket", "symbol", "type", "volume", "price_open", "price_current", "sl", "tp", "profit", "comment");
   int total = PositionsTotal();
   for(int i=0; i<total; i++)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      string typ = (PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY) ? "buy" : "sell";
      FileWrite(h,
         IntegerToString((long)ticket),
         PositionGetString(POSITION_SYMBOL),
         typ,
         DoubleToString(PositionGetDouble(POSITION_VOLUME), 2),
         DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN), 8),
         DoubleToString(PositionGetDouble(POSITION_PRICE_CURRENT), 8),
         DoubleToString(PositionGetDouble(POSITION_SL), 8),
         DoubleToString(PositionGetDouble(POSITION_TP), 8),
         DoubleToString(PositionGetDouble(POSITION_PROFIT), 2),
         PositionGetString(POSITION_COMMENT));
     }
   FileClose(h);
  }

void DumpDeals()
  {
   int h = OpenCsv("deals.csv");
   if(h == INVALID_HANDLE)
      return;
   FileWrite(h, "ticket", "symbol", "type", "volume", "price", "profit", "time");
   datetime to = TimeCurrent();
   datetime from = to - 30*24*60*60;
   HistorySelect(from, to);
   int total = HistoryDealsTotal();
   int start = MathMax(0, total-50);
   for(int i=start; i<total; i++)
     {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket==0)
         continue;
      FileWrite(h,
         IntegerToString((long)ticket),
         HistoryDealGetString(ticket, DEAL_SYMBOL),
         IntegerToString((int)HistoryDealGetInteger(ticket, DEAL_TYPE)),
         DoubleToString(HistoryDealGetDouble(ticket, DEAL_VOLUME), 2),
         DoubleToString(HistoryDealGetDouble(ticket, DEAL_PRICE), 8),
         DoubleToString(HistoryDealGetDouble(ticket, DEAL_PROFIT), 2),
         TimeToString((datetime)HistoryDealGetInteger(ticket, DEAL_TIME), TIME_DATE|TIME_SECONDS));
     }
   FileClose(h);
  }

void DumpSymbols()
  {
   int h = OpenCsv("symbols.csv");
   if(h == INVALID_HANDLE)
      return;
   FileWrite(h, "name", "path", "description", "digits", "point", "trade_contract_size", "tick_size", "tick_value", "volume_min", "volume_step", "volume_max", "visible");
   int total = SymbolsTotal(false);
   for(int i=0; i<total; i++)
     {
      string name = SymbolName(i, false);
      if(name=="")
         continue;
      FileWrite(h,
         name,
         SymbolInfoString(name, SYMBOL_PATH),
         SymbolInfoString(name, SYMBOL_DESCRIPTION),
         IntegerToString((int)SymbolInfoInteger(name, SYMBOL_DIGITS)),
         DoubleToString(SymbolInfoDouble(name, SYMBOL_POINT), 10),
         DoubleToString(SymbolInfoDouble(name, SYMBOL_TRADE_CONTRACT_SIZE), 2),
         DoubleToString(SymbolInfoDouble(name, SYMBOL_TRADE_TICK_SIZE), 10),
         DoubleToString(SymbolInfoDouble(name, SYMBOL_TRADE_TICK_VALUE), 8),
         DoubleToString(SymbolInfoDouble(name, SYMBOL_VOLUME_MIN), 4),
         DoubleToString(SymbolInfoDouble(name, SYMBOL_VOLUME_STEP), 4),
         DoubleToString(SymbolInfoDouble(name, SYMBOL_VOLUME_MAX), 4),
         IntegerToString((int)SymbolInfoInteger(name, SYMBOL_SELECT)));
     }
   FileClose(h);
  }

string SymbolFileKey(string symbol)
  {
   string invalid[] = {"<", ">", ":", "\"", "/", "\\", "|", "?", "*"};
   for(int i=0; i<ArraySize(invalid); i++)
      StringReplace(symbol, invalid[i], "_");
   return symbol;
  }

bool ParseTimeframe(const string name, ENUM_TIMEFRAMES &period)
  {
   if(name=="M1") period=PERIOD_M1;
   else if(name=="M5") period=PERIOD_M5;
   else if(name=="M15") period=PERIOD_M15;
   else if(name=="M30") period=PERIOD_M30;
   else if(name=="H1") period=PERIOD_H1;
   else if(name=="H4") period=PERIOD_H4;
   else if(name=="D1") period=PERIOD_D1;
   else if(name=="W1") period=PERIOD_W1;
   else return false;
   return true;
  }

bool DumpOneRates(const string symbol, const string timeframe, const ENUM_TIMEFRAMES period)
  {
   MqlRates rates[];
   int copied = CopyRates(symbol, period, 0, 300, rates);
   if(copied<=0)
      return false;
   string filename = "rates_"+SymbolFileKey(symbol)+"_"+timeframe+".csv";
   int h = OpenCsv(filename);
   if(h == INVALID_HANDLE)
      return false;
   FileWrite(h, "time", "open", "high", "low", "close", "tick_volume");
   for(int i=0; i<copied; i++)
      FileWrite(h,
         TimeToString(rates[i].time, TIME_DATE|TIME_SECONDS),
         DoubleToString(rates[i].open, 8),
         DoubleToString(rates[i].high, 8),
         DoubleToString(rates[i].low, 8),
         DoubleToString(rates[i].close, 8),
         IntegerToString((long)rates[i].tick_volume));
   FileClose(h);
   return true;
  }

bool DumpOneTick(const string symbol)
  {
   MqlTick tick;
   string filename = "tick_"+SymbolFileKey(symbol)+".csv";
   int h = OpenCsv(filename);
   if(h == INVALID_HANDLE)
      return false;
   FileWrite(h, "symbol", "bid", "ask", "last", "time");
   bool has_tick = SymbolInfoTick(symbol, tick);
   if(has_tick)
      FileWrite(h, symbol, DoubleToString(tick.bid, 8), DoubleToString(tick.ask, 8),
         DoubleToString(tick.last, 8), TimeToString(tick.time, TIME_DATE|TIME_SECONDS));
   FileClose(h);
   return has_tick;
  }

bool ValidRequestId(const string request_id)
  {
   if(StringLen(request_id)!=32)
      return false;
   for(int i=0; i<StringLen(request_id); i++)
     {
      ushort ch = StringGetCharacter(request_id, i);
      if(!((ch>='0' && ch<='9') || (ch>='a' && ch<='f')))
         return false;
     }
   return true;
  }

void ProcessMarketRequest()
  {
   string request_name = "desk\\market_request.txt";
   if(!FileIsExist(request_name, FILE_COMMON))
      return;
   int h = FileOpen(request_name, FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(h == INVALID_HANDLE)
      return;
   string request_id = FileReadString(h);
   if(!ValidRequestId(request_id))
     {
      FileClose(h);
      FileDelete(request_name, FILE_COMMON);
      return;
     }
   bool request_ok = true;
   while(!FileIsEnding(h))
     {
      string line = FileReadString(h);
      if(line=="")
         continue;
      int split_at = StringFind(line, "|");
      if(split_at <= 0)
         continue;
      string symbol = StringSubstr(line, 0, split_at);
      string timeframe_csv = StringSubstr(line, split_at+1);
      if(!SymbolSelect(symbol, true))
        {
         request_ok = false;
         continue;
        }
      string timeframes[];
      int count = StringSplit(timeframe_csv, ',', timeframes);
      if(count<=0)
         request_ok = false;
      for(int i=0; i<count; i++)
        {
         ENUM_TIMEFRAMES period;
         if(ParseTimeframe(timeframes[i], period))
           {
            if(!DumpOneRates(symbol, timeframes[i], period))
               request_ok = false;
           }
         else
            request_ok = false;
        }
      if(!DumpOneTick(symbol))
         request_ok = false;
     }
   FileClose(h);
   FileDelete(request_name, FILE_COMMON);

   string response_name = "desk\\market_response_"+request_id+".txt";
   int response = FileOpen(response_name, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(response != INVALID_HANDLE)
     {
      string result = request_ok ? "done" : "error";
      FileWriteString(response, request_id+"|"+result+"\r\n");
      FileFlush(response);
      FileClose(response);
     }
  }

void DumpRates()
  {
   string parts[];
   int n = StringSplit(WatchCSV, ',', parts);
   string tfs[] = {"M15","H1","H4","D1"};
   ENUM_TIMEFRAMES tfconst[] = {PERIOD_M15, PERIOD_H1, PERIOD_H4, PERIOD_D1};
   for(int s=0; s<n; s++)
     {
      string sym = parts[s];
      StringTrimLeft(sym);
      StringTrimRight(sym);
      if(sym=="")
         continue;
      SymbolSelect(sym, true);
      for(int t=0; t<ArraySize(tfs); t++)
         DumpOneRates(sym, tfs[t], tfconst[t]);
      DumpOneTick(sym);
     }
  }
