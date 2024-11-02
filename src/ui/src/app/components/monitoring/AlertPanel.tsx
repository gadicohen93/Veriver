// components/monitoring/AlertPanel.tsx
import { AlertGroup } from "@/components/ui/alert-group";
import { Tabs, TabsContent } from "@/components/ui/tabs";

export function AlertPanel() {
  return (
    <div className="h-full flex flex-col">
      <Tabs defaultValue="high">
        <TabsList>
          <TabsTrigger value="high">High Priority</TabsTrigger>
          <TabsTrigger value="medium">Medium Priority</TabsTrigger>
          <TabsTrigger value="low">Low Priority</TabsTrigger>
        </TabsList>
        <TabsContent value="high">
          <AlertGroup alerts={highPriorityAlerts} />
        </TabsContent>
        <TabsContent value="medium">
          <AlertGroup alerts={mediumPriorityAlerts} />
        </TabsContent>
        <TabsContent value="low">
          <AlertGroup alerts={lowPriorityAlerts} />
        </TabsContent>
      </Tabs>
    </div>
  );
}