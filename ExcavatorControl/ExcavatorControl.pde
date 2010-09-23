#include <Messenger.h>
#define a 5.81715
#define b -27.3537
#define c 35.53657
Messenger message = Messenger();
int select;
int power;
char device;
char outgoingControl;
float irDistance;
float irVoltage;

void sendCommand()
{
  if (device == 'm')
  {
    Serial1.write(outgoingControl);
  }
  else if (device == 'a')
  {
    Serial2.write(outgoingControl);
  }
}
    

void messageReady()
{
  while (message.available())
  {
    device = message.readChar();
    if (device == 'm' || device == 'a')
    {
      select = message.readInt();
      if (select == 1 || select == 3)
      {
        power = message.readInt();
        if (power == 0)
        {
          outgoingControl = 64;
        }
        else if (power < 0)
        {
          outgoingControl = power + 65;
        }
        else if (power > 0)
        {
          outgoingControl = power + 63;
        }
      }
      else if (select == 2 || select == 4)
      {
        power = message.readInt();
        if (power == 0)
        {
          outgoingControl = 192;
        }
        else if (power < 0)
        {
          outgoingControl = power + 192;
        }
        else if (power > 0)
        {
          outgoingControl = power + 191;
        }
      }
    }
    sendCommand();
  }   
}

void setup()
{
  Serial.begin(19200);
  Serial1.begin(19200);
  Serial2.begin(19200);
  message.attach(messageReady);
}

void loop() 
{
  while ( Serial.available() ) message.process(Serial.read () );
  pollIR();
}

void pollIR()
{
  irVoltage = ((analogRead(5))/1024.0)*5.0;
  if (irVoltage >= 0.5)
  {
    irVoltage = ((analogRead(5))/1024.0)*5.0;
    if (irVoltage >= 0.5)
    {
      irVoltage = ((analogRead(5))/1024.0)*5.0;
      if (irVoltage >= 0.5)
      {
      //  Serial.println(irVoltage);
      //  delay(250);
        irDistance = a*(irVoltage)*(irVoltage) + b*(irVoltage) + c;
        Serial.print("Backup Sensor: ");
        Serial.println(irDistance);
      }}
  }
}
  
