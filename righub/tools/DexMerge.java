import org.jf.dexlib2.DexFileFactory;
import org.jf.dexlib2.Opcodes;
import org.jf.dexlib2.iface.ClassDef;
import org.jf.dexlib2.iface.DexFile;
import org.jf.dexlib2.immutable.ImmutableDexFile;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

/** Keep every 1.5.1 class except HubActivity, and swap in the rebuilt HubActivity. */
public class DexMerge {
  public static void main(String[] args) throws Exception {
    DexFile base = DexFileFactory.loadDexFile(new File(args[0]), Opcodes.forApi(29));
    DexFile hub = DexFileFactory.loadDexFile(new File(args[1]), Opcodes.forApi(29));
    List<ClassDef> classes = new ArrayList<ClassDef>();
    for (ClassDef c : base.getClasses()) {
      if (c.getType().startsWith("Lcom/truckerchris/righub/HubActivity")) continue;
      classes.add(c);
    }
    int added = 0;
    for (ClassDef c : hub.getClasses()) {
      if (!c.getType().startsWith("Lcom/truckerchris/righub/HubActivity")) {
        throw new IllegalStateException("unexpected class in hub dex: " + c.getType());
      }
      classes.add(c);
      added++;
    }
    if (added < 1) throw new IllegalStateException("hub dex has no HubActivity");
    DexFileFactory.writeDexFile(args[2], new ImmutableDexFile(Opcodes.forApi(29), classes));
    System.out.println("classes=" + classes.size() + " hub=" + added);
  }
}
